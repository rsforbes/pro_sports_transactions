# nodriver handler guide

Setup, supported browsers, caveats, and troubleshooting for
`NodriverRequestHandler`. A runnable example lives in
[`examples/nodriver_search.py`](../examples/nodriver_search.py).

## Prerequisites

Designed for **Windows, macOS, and Linux**. So far it has been live-tested on Linux only (desktop-less, under `xvfb`), so please open an issue if you hit trouble on Windows or macOS. pip installs the library and the extra, but you must provide the browser and, on headless Linux, a display yourself:

1. **The library + extra** — `pip install pro_sports_transactions[nodriver]`. This installs `nodriver` and `opencv-python-headless`. It does **not** install a browser.
2. **A Chromium-based browser — Google Chrome recommended** — nodriver drives an existing browser install rather than downloading one. Google Chrome is the only browser tested so far; Edge, Brave, and others may work but are untested\* (see [Supported browsers](#supported-browsers)). If you already have Chrome, there's nothing to do; otherwise install it:
   - **Windows / macOS**: get Chrome from <https://www.google.com/chrome/> (default locations: `C:\Program Files\Google\Chrome\Application\chrome.exe`, `/Applications/Google Chrome.app`).
   - **Linux**: install the `google-chrome-stable` package.
   - **To use a browser other than Chrome**, or **if Chromium is also installed**, set `browser_executable_path` explicitly. nodriver only auto-detects Chrome and Chromium. When both are present it prefers the *shortest* path, so `/usr/bin/chromium` beats `/usr/bin/google-chrome` (and `Chromium.app` beats `Google Chrome.app` on macOS), and Chromium failed in our testing. Example: `NodriverConfig(browser_executable_path="/usr/bin/google-chrome-stable")`.
3. **A display** — the browser runs headful (with a window), not in headless mode.
   - **Windows, macOS, or Linux with a desktop**: nothing extra to install. Expect a browser window to open briefly while it solves the challenge.
   - **Headless Linux only** (server, container, CI, WSL without a desktop): install `xvfb` and launch under it, e.g. `xvfb-run -a python your_script.py`. The window is drawn on xvfb's invisible virtual display, so nothing appears on screen. Headless mode does not reliably clear the challenge. `xvfb` is Linux-only and is neither needed nor available on Windows/macOS.

### Running without a visible window

Windows and macOS have no built-in equivalent of xvfb, so there is no supported way to hide the browser window on those systems directly. Options:

- **Run inside Linux (tested).** Use Docker on Windows or macOS, or WSL2 on Windows, with Chrome and `xvfb` installed, and launch under `xvfb-run -a`. This is how the project's dev container runs the live integration test, and nothing appears on your screen.
- **Push the window out of sight (untested).** Chrome flags such as `--window-position=-32000,-32000` (off-screen) or `--start-minimized` can be passed with `NodriverConfig(browser_args=["--disable-dev-shm-usage", "--window-position=-32000,-32000"])`. Keep `--disable-dev-shm-usage` in the list, because setting `browser_args` replaces the default. Chrome may throttle rendering in hidden or minimized windows, and `verify_cf()` must locate and click the Turnstile checkbox, so the challenge may stop clearing.
- **Windows/macOS servers with no logged-in user (untested, likely to fail).** A Windows service has no interactive desktop, and macOS needs a logged-in graphical session for windows to render. Prefer the Linux route above.

### Supported browsers

nodriver drives the browser over the Chrome DevTools Protocol (CDP), so only Chromium-based browsers can be driven at all. Beyond that, what matters is whether Cloudflare clears the challenge in a given browser, which has only been verified for Chrome:

| Browser | Status |
| --- | --- |
| **Google Chrome** (stable) | ✅ Tested — the recommended choice |
| Chromium (unbranded) | ⚠️ Not recommended. Playwright's bundled Chromium failed in testing (the challenge never cleared); other Chromium builds are untested\* |
| Microsoft Edge, Brave, other Chromium-based browsers | ⚠️ Untested\* — may work. nodriver never auto-detects them; point `browser_executable_path` at the browser's executable |
| Firefox, Safari | ❌ Not possible — nodriver only speaks CDP and cannot control them |

\* *Untested* means we haven't tried it, not that it fails. If you try one, please open an issue with the result so this table can be updated.

## Caveats

Know these before choosing nodriver:

- **The session is bound to the browser and network.** `cf_clearance` only works with the exact user-agent of the browser that earned it, and Cloudflare typically ties it to your IP address as well. Switching VPNs or rotating proxies invalidates it and triggers a new browser solve. `NodriverConfig` has no proxy option (unlike `UnflareConfig`).
- **The cache is in-memory and per-process.** Each new Python process launches the browser and solves again (several seconds, a few hundred MB of RAM). Keep one handler alive and reuse it across searches rather than creating one per request.
- **On a desktop, a browser window opens** during the solve; that is expected. Under `xvfb` nothing is visible (see [Prerequisites](#prerequisites)).
- **The browser's sandbox is off by default** (`NodriverConfig(sandbox=False)`), because the Chromium sandbox usually fails inside containers. On a desktop you can set `sandbox=True`.
- **Shutdown noise.** When the program exits, nodriver may print an `Event loop is closed` traceback from its browser-teardown callbacks. It is harmless and does not affect results.
- **It's an arms race.** The bypass depends on nodriver's `verify_cf()` clicking Cloudflare's Turnstile checkbox. When Cloudflare changes, it may stop working until nodriver is updated; the `nodriver>=0.50,<1` pin may need bumping. Unflare remains available as a fallback.
- **Be a good citizen.** Bypassing the challenge doesn't remove the site's rate limits or terms of use. Keep request volume reasonable.

## Troubleshooting

### nodriver: request returns `None` / challenge never clears
- **Occasional failure**: a single failed solve can happen; retry it (see [Handling failures and retries](../README.md#handling-failures-and-retries)). The causes below apply when it fails consistently.
- **Which browser launched?** Google Chrome is the only browser verified to clear the challenge; Playwright's bundled Chromium failed in testing. If Chromium is installed alongside Chrome, auto-detect may pick Chromium (it prefers the shortest path), so set `NodriverConfig(browser_executable_path=...)` to your Chrome binary. If you're using Edge, Brave, or another untested browser and it never clears, try Chrome. See [Supported browsers](#supported-browsers).
- **Changed IP / VPN**: a cached session issued to one IP may be rejected from another; the handler then re-solves automatically, which costs another browser launch.
- **Headless host**: run under a virtual display (`xvfb-run -a ...`); headless mode does not reliably solve the managed challenge.
- **opencv can't load**: `verify_cf()` imports `cv2` from `opencv-python-headless` (installed by the extra) to find the Turnstile checkbox. If it can't load, the checkbox is never clicked. Check with `python -c "import cv2"`. The OpenCV packages (`opencv-python`, `opencv-python-headless`, `opencv-contrib-python`, ...) all install the same `cv2` module and conflict with each other, so keep only one. If you installed an earlier release of the extra, it brought in `opencv-python`; `pip uninstall opencv-python opencv-python-headless` then `pip install --force-reinstall opencv-python-headless` leaves a single clean copy. If your project needs the GUI build for other reasons, keep `opencv-python` instead: it works with `verify_cf()` too.

### nodriver: `ImportError: NodriverRequestHandler requires the 'nodriver' extra...`
- **Cause**: the `nodriver` package isn't installed. `NodriverRequestHandler()` checks at construction so the problem surfaces immediately rather than as an empty result.
- **Solution**: `pip install pro_sports_transactions[nodriver]`.

### nodriver: `RuntimeError: Event loop is closed` at exit
- **Harmless**: nodriver's browser-teardown callbacks can fire after the event loop has shut down. Results are unaffected.
