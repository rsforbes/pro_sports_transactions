# nodriver Integration — In-Process Cloudflare Bypass

**Status:** implemented (opt-in plugin) · **Branch:** `feature/nodriver-integration` · **Date:** 2026-07-11 · **Last updated:** 2026-10-03

> User-facing setup, supported browsers, and caveats live in the main
> [README](../../README.md#prerequisites). This document is the design record.

## What shipped on this branch

- `CachedCredentialHandler` base (in `handlers/base_handler.py`) — owns the
  credential cache + fast `aiohttp` replay. `UnflareRequestHandler` now subclasses
  it (behaviour unchanged; all prior tests pass) and implements only its
  service-specific `_refresh_cache_and_request`.
- `NodriverRequestHandler` (`handlers/nodriver_handler.py`) — the user-facing
  handler. It only orchestrates: ask the credential source for credentials, cache
  them, replay over the shared cache/replay path. It is assembled from one-class-
  per-file building blocks, grouped by what they depend on:

  | Class | File | Responsibility |
  | --- | --- | --- |
  | `NodriverConfig` | `nodriver/nodriver_config.py` | User settings (re-exported from `handlers`) |
  | `BrowserSession` | `nodriver/browser_session.py` | Launch/reuse/close the browser; fail fast on a missing extra; relaunch on an event-loop change |
  | `NodriverCredentialSource` | `nodriver/nodriver_credential_source.py` | Load the URL, clear the challenge, return `Credentials` (never the page) |
  | `CookieHarvester` | `nodriver/cookie_harvester.py` | Read the cookies for one host from a nodriver browser (domain-suffix match) |
  | `Credentials` | `cloudflare/credentials.py` | Cookies + user-agent value object, shared by any Cloudflare bypass |
  | `LoopBoundLock` | `concurrency/loop_bound_lock.py` | An `asyncio.Lock` recreated per event loop (single-flight solves) |

  Only `nodriver/` depends on the optional `nodriver` package; `cloudflare/` and
  `concurrency/` import with the base install.

  Each has a small public interface and its own unit tests, so the handler's tests
  replace collaborators instead of patching private methods. Applying the same
  structure to the shipped handlers is tracked in #49.
- `[nodriver]` optional extra in `pyproject.toml` (`nodriver`, `opencv-python`).
  Chrome and (on headless hosts) xvfb are external prerequisites.
- Unit tests (fully mocked): `tests/unit/nodriver/` (one file per class) and
  `tests/unit/handlers/test_nodriver_handler.py` (orchestration).

**Verified live end-to-end (2026-10-03):** the integration test
(`tests/integration/handlers/test_nodriver_handler_integration.py`, run under
`xvfb-run -a` in the dev container) clears the challenge in Chrome on the first
request, then serves the second request and a full `Search` through the **cached
`aiohttp` replay path**, with `is_cache_valid()` true after the first solve. The
harvested `cf_clearance` + UA work with a plain HTTP client from the same IP, so only
the first request pays the browser cost. Replay requires that only the browser's UA is
sent: `_try_cached_request` merges caller headers case-insensitively so a caller's
lowercase `user-agent` cannot ride along with the cached `User-Agent`.

**Hardening from code review:**
- Cache expiry anchors on the `cf_clearance` cookie specifically — neither a
  short-lived `__cf_bm` (which would cap it) nor an unrelated long-lived
  first-party cookie (which would extend it past the real session) affects it.
- A double-checked lock stops concurrent cold-start requests from double-solving.
- Cookie host filtering uses a proper domain-suffix match, not substring.
- **Like `UnflareRequestHandler`, the browser is purely a credential factory: the
  page it loaded is never returned.** After a solve, the result always comes from
  replaying the harvested `cf_clearance` + UA over plain `aiohttp`; if that replay
  fails, the result is `None`. So the first response and all later cached responses
  are the same raw server HTML, and a Cloudflare block page (error 1020) or Chrome
  net-error page — which lack the challenge marker, and may sit beside a leftover
  `cf_clearance` in the reused browser's jar — can never reach the parser. A
  leftover cookie that is still valid is simply used (Cloudflare does not reissue a
  live one), keeping re-solves cheap.
- The solve gives up early (no replay) while the challenge marker (`_cf_chl`) is
  still present. A `cf_clearance` is **not** required: Cloudflare may serve the page
  without a challenge (and so without issuing one), and the replay decides success
  either way. `challenge-platform` is deliberately not a marker (Cloudflare's beacon
  injects it into normal pages too).
- The browser connection and solve lock belong to the event loop that created them.
  Each `asyncio.run()` creates and then closes a new loop, so a handler reused across
  `asyncio.run()` calls detects the loop change, stops the old browser, and launches a
  new one (observed live: without this, the reused connection hung `get()`
  indefinitely).
- Browser/CDP exceptions are contained, preserving the `None`-on-failure contract
  the sibling `UnflareRequestHandler` honors.
- The solve loop re-checks once after the final `verify_cf`, so a last-attempt
  clear is not misreported as a failure.
- Transient network errors on the cached replay retry a few times instead of
  escalating a blip into a full browser re-solve.

Known rough edges / deferred:
- On interpreter/loop shutdown nodriver can emit a benign "Event loop is closed"
  traceback from its browser-teardown callbacks; it does not affect `get()`.
- The shared replay opens a fresh `aiohttp.ClientSession` per request (no
  connection pooling). A persistent pooled session is a worthwhile follow-up but
  adds session lifecycle/close semantics to both handlers; deferred.

## Goal

Replace the external **Unflare** sidecar service with an **in-process** request handler so
end users can `pip install pro_sports_transactions` and retrieve data without running a
separate container. Same Cloudflare-bypass technique Unflare uses, but importable directly
into the Python library.

## Background: why the HTTP-client approaches can't work

prosportstransactions.com (PST) is behind a Cloudflare **Managed Challenge** that embeds an
**interactive Turnstile checkbox** in a nested iframe. The challenge response is a ~6 KB
"Just a moment…" page containing `challenge-platform`, `_cf_chl`, and `window._cf`.

Re-tested live on 2026-07-11:

| Approach | Result |
| --- | --- |
| Plain `curl` / direct request | `403 cf-mitigated: challenge` |
| **curl_cffi 0.15.0** (chrome124/131/136, safari18, firefox135, chrome99_android) | 403 on every target |
| tls-client (bogdanfinn, actively maintained) | Same TLS layer — cannot solve a JS challenge |
| cloudscraper | Abandoned; does not clear current Cloudflare |
| Vanilla Playwright (headless) | Hangs on "Just a moment…" |
| nodriver (headless) | Hangs on "Just a moment…" |
| nodriver + Playwright's **Chromium** (headful/Xvfb) | Hangs on "Just a moment…" |

All fingerprint-based tools aim at the wrong layer: the gate is not TLS, it is an
interactive JS challenge that must be **executed and clicked** in a real browser.

## Verified solution

Tested from the user's own machine (dev container runs locally, so the egress IP is the
**same residential IP Unflare uses** — IP reputation is not a factor). Each element below was
individually necessary; removing any one caused the challenge to loop forever.

1. **nodriver** (`pip install nodriver`, tested 0.50.3) — successor to
   undetected-chromedriver; drives Chrome over CDP directly with no Playwright/Puppeteer
   shim, so there is no automation-protocol leak to patch.
2. **Real Google Chrome** (`/usr/bin/google-chrome-stable`), **not** Chromium. Playwright's
   bundled Chromium failed; real Chrome worked. Unbranded Chromium is detectable.
3. **Headful under Xvfb** on a headless host (`xvfb-run -a`). Headless failed for every tool.
4. **`page.verify_cf()`** to click the Turnstile checkbox — requires **`opencv-python`**
   (verify_cf locates the checkbox via CV template matching). Passive waiting never clears it.

Result: first verify attempt returned `Basketball Transactions Search Results`, 394 KB,
27 rows of real data (e.g. `1937-07-01 | Metros (NBL) | Bill Hosket | acquired`).

### Minimal reproduction

```python
import asyncio, nodriver as uc

URL = (
    "https://www.prosportstransactions.com/basketball/Search/SearchResults.php"
    "?Player=&Team=&BeginDate=&EndDate=&PlayerMovementChkBx=yes&submit=Search"
)


async def main():
    browser = await uc.start(
        browser_executable_path="/usr/bin/google-chrome-stable",
        headless=False,  # run under Xvfb on a headless host
        browser_args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    page = await browser.get(URL)
    for _ in range(8):
        html = await page.get_content()
        if "_cf_chl" not in html:  # challenge-only marker (see handler)
            break
        await page.verify_cf()  # clicks the Turnstile checkbox (needs opencv-python)
        await asyncio.sleep(5)
    print(len(html))
    browser.stop()


uc.loop().run_until_complete(main())
```

## How Unflare does it (for comparison)

Unflare uses `puppeteer-real-browser` (TypeScript/Node), runs real Chrome headful under
Xvfb, clicks the Turnstile checkbox, and returns `cf_clearance` + user-agent via a `/scrape`
HTTP endpoint. **Same fundamental technique** as nodriver — the difference is implementation:

| | Unflare | nodriver |
| --- | --- | --- |
| Language | TypeScript / Node | **Python** |
| Driver | `puppeteer-real-browser` (patched Puppeteer) | raw CDP, no shim |
| Anti-detection | patches Puppeteer's `Runtime.enable` CDP leak | avoids the leak (no shim) |
| Deployment | **separate HTTP service** (sidecar) | **in-process** `import nodriver` |

Because Unflare is Node, a Python library cannot embed it — hence the sidecar. nodriver being
Python is the entire reason it can replace the service in-process. Neither bypasses Cloudflare
"better"; they are the same tier. The win is purely DX: importable vs. separate container.

## Proposed architecture

A `NodriverRequestHandler` implementing the existing `RequestHandler` interface:

- Keep **one warm browser** for the process lifetime (browser startup is the dominant cost).
- On first request (or on 403/challenge), solve the challenge and capture `cf_clearance` +
  the exact user-agent.
- **Reuse the cookie + UA for fast follow-up requests** (plain HTTP or a lightweight client),
  re-solving only when the cookie expires. This gives near-HTTP speed after the first solve
  and uses the browser only for (re)solving.
- Fall back to re-solving on any renewed `cf-mitigated: challenge` response.

## Dependencies & caveats

- Ships a heavier stack than pure HTTP: a **real Chrome** binary, **Xvfb** (for headless
  servers), and **opencv-python**. Closer to Playwright's `install-deps` than a plain wheel.
- Per-solve cost: a few seconds and a few hundred MB RAM.
- It remains an arms race — nodriver / `verify_cf` will need periodic updates as Cloudflare
  changes. This is the maintenance burden Unflare/FlareSolverr currently absorb.
- Chromium does **not** substitute for Google Chrome here (documented in the README's
  "Supported browsers" table).
- nodriver's `find_chrome_executable()` also matches `chromium`/`chromium-browser`/`chrome`
  on Linux and `Chromium.app` on macOS, and picks the **shortest** path when several exist,
  so with Chromium installed alongside Chrome, auto-detect can silently choose Chromium.
  On Windows it only searches Chrome stable/Beta/Canary install dirs.
- Browser scope: nodriver is CDP-only, so Firefox/Safari are impossible. Edge/Brave are
  CDP-capable but never auto-detected and untested against Cloudflare.
- Live testing so far is Linux-only (dev container, WSL2 + xvfb); Windows/macOS untested.

## Open questions / next steps

- [x] Prototype `NodriverRequestHandler` against the existing handler interface.
- [x] Validate `cf_clearance` reuse — confirmed: replaying the harvested cookie + UA
      with plain `aiohttp` from the same IP works (see live result above).
- [x] Package as an optional extra (`pip install pro_sports_transactions[nodriver]`);
      Unflare remains the documented default until nodriver is proven in the wild.
- [x] README: document the handler, the extra, the Chrome/xvfb prerequisites, supported
      browsers, and caveats.
- [x] Add an example (`examples/nodriver_search.py`) mirroring `unflare_search.py`.
- [ ] CI: unit tests run without the extra; consider an opt-in integration job that
      installs Chrome + xvfb and exercises a real solve.
- [ ] Headless-with-patches investigation: can we avoid the xvfb requirement on servers?
- [ ] Keep the Unflare handler as a fallback; do not remove until nodriver is proven.
- [ ] Live-test on Windows and macOS desktops.
- [ ] Warn (or fail fast) when the launched binary looks like unbranded Chromium.
- [ ] Consider persisting the cached `cf_clearance` across processes (observed lifetime
      ~1 year on PST) to avoid a browser solve per run.
