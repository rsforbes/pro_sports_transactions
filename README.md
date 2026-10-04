[![Version: PyPI](https://img.shields.io/pypi/v/pro_sports_transactions.svg?longCache=true&style=for-the-badge&logo=pypi)](https://pypi.python.org/pypi/pro_sports_transactions)
![Total Downloads](https://img.shields.io/pepy/dt/pro_sports_transactions?style=for-the-badge)
[![License: MIT](https://img.shields.io/github/license/rsforbes/pro_sports_transactions.svg?style=for-the-badge)](https://github.com/rsforbes/pro_sports_transactions/blob/master/LICENSE)

# Pro Sports Transactions API
Pro Sports Transactions is a Python API client-library for https://www.prosportstransactions.com enabling software engineers, data scientists, and sports fans with the ability to easily retrieve trades, free agent movements, signings, injuries, disciplinary actions, legal/criminal actions, and much more for five of the North American professional leagues: MLB, MLS, NBA, NFL, and NHL.

## What is sports data without the transactions?
- "Did he just throw his mouthpiece into the stands?"
- "Yep."

`2023-01-27	| Warriors | • Stephen Curry | fined $25,000 by NBA for throwing his mouthpiece into the stands`

## Features

- 🏀 **Multi-Sport Support**: MLB, MLS, NBA, NFL, and NHL
- 🚀 **Multiple Request Handlers**: In-process Cloudflare bypass (`NodriverRequestHandler`) or the Unflare sidecar (`UnflareRequestHandler`)
- ⚡ **Performance Testing**: Built-in configurable performance benchmarks
- 🧪 **Comprehensive Testing**: Unit, integration, and performance test suites
- 📊 **Multiple Output Formats**: DataFrame, dict, or JSON
- 🔧 **Configurable**: Performance thresholds and request handling options
## ⚠️ Important Notice

**prosportstransactions.com is protected by a Cloudflare challenge, direct requests are typically blocked.** You'll need a Cloudflare-bypass request handler. Two are provided:

- **`NodriverRequestHandler`** — solves the challenge **in-process** with a real browser (via [nodriver](https://github.com/ultrafunkamsterdam/nodriver)). Enable it with the `nodriver` extra: `pip install pro_sports_transactions[nodriver]`. The extra installs `nodriver` + `opencv-python` only — you also need a Chromium-based browser installed (nodriver uses an existing install; it does not download one). Google Chrome is the tested choice; others are untested (see [Supported browsers](#supported-browsers)). On a headless Linux host you also need a virtual display such as `xvfb`. Designed for Windows, macOS, and Linux (live-tested on Linux so far); see [Prerequisites](#prerequisites).
- **`UnflareRequestHandler`** — delegates [Unflare](https://github.com/iamyegor/Unflare), a sidecar (container), that you run alongside your app.

Both perform the same underlying bypass (a real browser clears the challenge and hands back a `cf_clearance` session that is cached and replayed). Choose nodriver to avoid running a sidecar, or Unflare to keep the browser stack out of your application process. See [Choosing a handler](#choosing-a-handler).
  
# Getting Started

## Prerequisites

Due to Cloudflare protection, you need a bypass handler. Pick one:

**Option A — nodriver (in-process, no separate service):**

Designed for **Windows, macOS, and Linux**. So far it has been live-tested on Linux only (desktop-less, under `xvfb`), so please open an issue if you hit trouble on Windows or macOS. pip installs the library and the extra, but you must provide the browser and, on headless Linux, a display yourself:

1. **The library + extra** — `pip install pro_sports_transactions[nodriver]`. This installs `nodriver` and `opencv-python`. It does **not** install a browser.
2. **A Chromium-based browser — Google Chrome recommended** — nodriver drives an existing browser install rather than downloading one. Google Chrome is the only browser tested so far; Edge, Brave, and others may work but are untested\* (see [Supported browsers](#supported-browsers)). If you already have Chrome, there's nothing to do; otherwise install it:
   - **Windows / macOS**: get Chrome from <https://www.google.com/chrome/> (default locations: `C:\Program Files\Google\Chrome\Application\chrome.exe`, `/Applications/Google Chrome.app`).
   - **Linux**: install the `google-chrome-stable` package.
   - **To use a browser other than Chrome**, or **if Chromium is also installed**, set `browser_executable_path` explicitly. nodriver only auto-detects Chrome and Chromium. When both are present it prefers the *shortest* path, so `/usr/bin/chromium` beats `/usr/bin/google-chrome` (and `Chromium.app` beats `Google Chrome.app` on macOS), and Chromium failed in our testing. Example: `NodriverConfig(browser_executable_path="/usr/bin/google-chrome-stable")`.
3. **A display** — the browser runs headful (with a window), not in headless mode.
   - **Windows, macOS, or Linux with a desktop**: nothing extra to install. Expect a browser window to open briefly while it solves the challenge.
   - **Headless Linux only** (server, container, CI, WSL without a desktop): install `xvfb` and launch under it, e.g. `xvfb-run -a python your_script.py`. The window is drawn on xvfb's invisible virtual display, so nothing appears on screen. Headless mode does not reliably clear the challenge. `xvfb` is Linux-only and is neither needed nor available on Windows/macOS.

#### Running without a visible window

Windows and macOS have no built-in equivalent of xvfb, so there is no supported way to hide the browser window on those systems directly. Options:

- **Run inside Linux (tested).** Use Docker on Windows or macOS, or WSL2 on Windows, with Chrome and `xvfb` installed, and launch under `xvfb-run -a`. This is how the project's dev container runs the live integration test, and nothing appears on your screen.
- **Push the window out of sight (untested).** Chrome flags such as `--window-position=-32000,-32000` (off-screen) or `--start-minimized` can be passed with `NodriverConfig(browser_args=["--disable-dev-shm-usage", "--window-position=-32000,-32000"])`. Keep `--disable-dev-shm-usage` in the list, because setting `browser_args` replaces the default. Chrome may throttle rendering in hidden or minimized windows, and `verify_cf()` must locate and click the Turnstile checkbox, so the challenge may stop clearing.
- **Windows/macOS servers with no logged-in user (untested, likely to fail).** A Windows service has no interactive desktop, and macOS needs a logged-in graphical session for windows to render. Prefer the Linux route above.

A runnable example lives in [`examples/nodriver_search.py`](examples/nodriver_search.py).

#### Supported browsers

nodriver drives the browser over the Chrome DevTools Protocol (CDP), so only Chromium-based browsers can be driven at all. Beyond that, what matters is whether Cloudflare clears the challenge in a given browser, which has only been verified for Chrome:

| Browser | Status |
| --- | --- |
| **Google Chrome** (stable) | ✅ Tested — the recommended choice |
| Chromium (unbranded) | ⚠️ Not recommended. Playwright's bundled Chromium failed in testing (the challenge never cleared); other Chromium builds are untested\* |
| Microsoft Edge, Brave, other Chromium-based browsers | ⚠️ Untested\* — may work. nodriver never auto-detects them; point `browser_executable_path` at the browser's executable |
| Firefox, Safari | ❌ Not possible — nodriver only speaks CDP and cannot control them |

\* *Untested* means we haven't tried it, not that it fails. If you try one, please open an issue with the result so this table can be updated.

**Option B — Unflare (separate service):**

1. **Install and run Unflare service**: Follow the setup instructions at [https://github.com/iamyegor/Unflare](https://github.com/iamyegor/Unflare)
2. **Start the Unflare service** (typically runs on `http://localhost:5002`)
3. **Use `UnflareRequestHandler`** in your code (see examples below)

### Choosing a handler

| | `NodriverRequestHandler` | `UnflareRequestHandler` |
| --- | --- | --- |
| Separate service to run | No — in-process | Yes — the Unflare sidecar |
| Extra install footprint | Chromium-based browser (Chrome recommended) + `nodriver` extra + `xvfb` on servers | A running Unflare/Docker service |
| Best when | You want a single `pip install` and no sidecar | You'd rather keep the browser stack out of your app process (e.g. a shared solver container) |

Both cache the `cf_clearance` session after the first solve and replay cheap HTTP requests until it expires.

All handlers are used the same way, so switching is a one-line change:

```python
async with NodriverRequestHandler() as handler:   # or UnflareRequestHandler(), DirectRequestHandler()
    df = await pst.Search(..., request_handler=handler).get_dataframe()
```

Each constructor takes an optional config (`NodriverConfig`, `UnflareConfig`) and works with its defaults. `async with` calls `close()` on exit; for nodriver that shuts down the browser, for the others it's a no-op, so the same code is correct for every handler.

### nodriver caveats

Know these before choosing nodriver:

- **The session is bound to the browser and network.** `cf_clearance` only works with the exact user-agent of the browser that earned it, and Cloudflare typically ties it to your IP address as well. Switching VPNs or rotating proxies invalidates it and triggers a new browser solve. `NodriverConfig` has no proxy option (unlike `UnflareConfig`).
- **The cache is in-memory and per-process.** Each new Python process launches the browser and solves again (several seconds, a few hundred MB of RAM). Keep one handler alive and reuse it across searches rather than creating one per request.
- **On a desktop, a browser window opens** during the solve; that is expected. Under `xvfb` nothing is visible (see [Prerequisites](#prerequisites)).
- **The browser's sandbox is off by default** (`NodriverConfig(sandbox=False)`), because the Chromium sandbox usually fails inside containers. On a desktop you can set `sandbox=True`.
- **Shutdown noise.** When the program exits, nodriver may print an `Event loop is closed` traceback from its browser-teardown callbacks. It is harmless and does not affect results.
- **It's an arms race.** The bypass depends on nodriver's `verify_cf()` clicking Cloudflare's Turnstile checkbox. When Cloudflare changes, it may stop working until nodriver is updated; the `nodriver>=0.50,<1` pin may need bumping. Unflare remains available as a fallback.
- **Be a good citizen.** Bypassing the challenge doesn't remove the site's rate limits or terms of use. Keep request volume reasonable.

## New to async Python?

The examples use Python's `async` features because fetching web pages involves a lot of waiting. You only need three ideas:

- `async def` defines a function that can wait without freezing your program.
- `await` runs one of those functions and waits for its result. You can only write `await` inside an `async def` function (or in Jupyter, see below).
- `asyncio.run(...)` starts everything from a normal script.

### Running the examples in Jupyter

Jupyter notebooks already run async code for you, so **don't use `asyncio.run()` in a notebook**. It fails with:

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

Instead, `await` the function directly in a cell:

```python
df = await search_transactions()   # in a notebook cell, instead of asyncio.run(search_transactions())
```

### Do I have to use `async with`?

`async with` makes sure the handler cleans up after itself when the block ends, even if an error happens partway through. What "cleaning up" means depends on the handler:

- **nodriver**: shuts down the browser it started. This is the one that matters.
- **Unflare** and **direct**: nothing to clean up (the Unflare browser runs in its own separate service). `async with` still works, so you can switch handlers without changing your code.

You can skip `async with` and just create the handler:

```python
handler = NodriverRequestHandler()
df = await pst.Search(..., request_handler=handler).get_dataframe()
```

That's fine in a script: the browser is shut down when the script ends. In a **notebook** or any program that keeps running, the browser would keep running in the background (using memory) until you restart the kernel or the program exits. There, use `async with`, or call `await handler.close()` when you're done.

## Quick Start with nodriver
```python
from datetime import date
import asyncio
import pro_sports_transactions as pst
from pro_sports_transactions.handlers import NodriverRequestHandler, NodriverConfig

# In-process Cloudflare bypass — no separate service required.
# browser_executable_path defaults to auto-detect (Chrome/Chromium); set it
# to point at a specific browser. On a headless host, run under xvfb (see Prerequisites).
config = NodriverConfig()

async def search_transactions():
    async with NodriverRequestHandler(config) as handler:  # closes the browser on exit
        return await pst.Search(
            league=pst.League.NBA,
            transaction_types=tuple(pst.TransactionType),
            start_date=date.fromisoformat("2022-10-18"),
            end_date=date.fromisoformat("2023-04-09"),
            player="LeBron James",
            team="Lakers",
            request_handler=handler,  # IMPORTANT: use the bypass handler
        ).get_dataframe()  # Also supports get_dict() and get_json()

if __name__ == "__main__":
    df = asyncio.run(search_transactions())
```

## Quick Start with Unflare
```python
from datetime import date
import asyncio
import pro_sports_transactions as pst
from pro_sports_transactions.handlers import UnflareRequestHandler, UnflareConfig

# Configure Unflare handler (bypasses Cloudflare via the Unflare service)
config = UnflareConfig(url="http://localhost:5002/scrape")  # Your Unflare service URL

# League (MLB, MLS, NBA, NFL, and NHL)
league = pst.League.NBA

# Transaction types: Disciplinary Actions, Injured List, Injuries,
# Legal Incidents, Minor League To/For, Personal Reasons,
# and Movement (e.g., Trades, Acquisitions, Waivers, Draft Picks, etc.)
transaction_types = tuple([t for t in pst.TransactionType])

# Date range: 2022-23 NBA Regular Season
start_date = date.fromisoformat("2022-10-18")
end_date = date.fromisoformat("2023-04-09")

# Pagination: Pro Sports Transactions provides 25 rows per page
starting_row = 0

# Define the coroutine for searching transactions
async def search_transactions():
    async with UnflareRequestHandler(config) as handler:  # same pattern as every handler
        return await pst.Search(
            league=league,
            transaction_types=transaction_types,
            start_date=start_date,
            end_date=end_date,
            player="LeBron James",
            team="Lakers",
            starting_row=starting_row,
            request_handler=handler,  # IMPORTANT: use the bypass handler
        ).get_dataframe()  # Also supports get_dict() and get_json()

# Example execution block
if __name__ == "__main__":
    df = asyncio.run(search_transactions())
```

## Direct Usage (May Not Work)
```python
# Passing no request_handler issues a direct request (the default). Direct
# requests are typically blocked by Cloudflare — shown here for completeness.

async def search_transactions_direct():
    return await pst.Search(
        league=pst.League.NBA,
        transaction_types=tuple(pst.TransactionType),
        player="LeBron James",
    ).get_dataframe()
```

## Advanced Usage

### Request Handlers

The library supports different request handlers for various scenarios:

#### Nodriver Handler (In-Process Cloudflare Bypass)
```python
from pro_sports_transactions.handlers import NodriverRequestHandler, NodriverConfig

# Requires the `nodriver` extra and a Chromium-based browser (Chrome recommended):
#   pip install pro_sports_transactions[nodriver]
config = NodriverConfig(
    browser_executable_path=None,  # None = auto-detect Chrome/Chromium; or set an explicit path
    headless=False,                # keep False; use xvfb on headless hosts
    verify_attempts=8,             # max Turnstile solve attempts
    solve_timeout=120.0,           # give up on one browser solve after this many seconds
)
handler = NodriverRequestHandler(config)

search = pst.Search(
    league=pst.League.NBA,
    transaction_types=(pst.TransactionType.Movement,),
    request_handler=handler,
)

# The first request drives the browser to clear the challenge and caches the
# resulting cf_clearance session; later requests replay it over plain HTTP.
print(f"Cache valid: {handler.is_cache_valid()}")

# Reuse one handler across many requests to keep the browser warm, then close it:
await handler.close()   # or use `async with handler:` as a context manager
```

#### Unflare Handler (Cloudflare Bypass via Service)
```python
from pro_sports_transactions.handlers import UnflareRequestHandler, UnflareConfig

# Configure the Unflare service connection
# First, set up Unflare: https://github.com/iamyegor/Unflare
config = UnflareConfig(
    url="http://localhost:5002/scrape",  # Your Unflare service URL
    timeout=60000,  # Request timeout in milliseconds
    proxy={"host": "proxy.example.com", "port": 8080}  # Optional proxy
)

handler = UnflareRequestHandler(config)
search = pst.Search(
    league=pst.League.NBA,
    transaction_types=(pst.TransactionType.Movement,),
    request_handler=handler
)

# The handler automatically caches cookies for improved performance
print(f"Cache valid: {handler.is_cache_valid()}")
print(f"Has cached cookies: {handler.has_cached_cookies}")
```

#### Direct Handler (Not Recommended - Often Blocked)

Direct requests are the **default**: constructing `Search(...)` without a `request_handler` already issues a direct request (equivalent to passing `DirectRequestHandler()`), so there's no need to wire it up explicitly — see [Direct Usage (May Not Work)](#direct-usage-may-not-work). `DirectRequestHandler` remains exported for callers that want to pass a handler explicitly. Either way, direct requests are typically blocked by Cloudflare; use a bypass handler for reliable access.

### Handling failures and retries

The handlers don't retry failed solves for you; retry policy is left to your application. When a handler can't clear Cloudflare, its `get()` returns `None`, and `Search` does **not** raise. It returns an empty result with the failure recorded in `errors`:

- `get_dataframe()`: an empty DataFrame with `df.attrs["errors"]` set
- `get_dict()` / `get_json()`: an `"errors"` key

An empty result without `errors` means the search genuinely matched nothing. So always check `errors` before trusting an empty result.

Occasional solve failures are expected (the Turnstile check doesn't pass every time), and a retry usually starts a fresh attempt: each new request after a failure makes the handler load the page again. A simple pattern:

```python
import asyncio

async def get_dataframe_with_retry(search, attempts=3):
    for attempt in range(attempts):
        df = await search.get_dataframe()
        if "errors" not in df.attrs:
            return df
        if attempt + 1 < attempts:
            await asyncio.sleep(2 ** attempt)  # back off: 1s, 2s, ...
    return df  # still failing; inspect df.attrs["errors"]

async with NodriverRequestHandler() as handler:
    search = pst.Search(..., request_handler=handler)
    df = await get_dataframe_with_retry(search)
```

Notes:
- Reuse the **same handler** across retries; with nodriver this keeps the browser running, so a retry doesn't pay for another launch (unless the browser itself crashed, in which case the handler relaunches it). [`examples/nodriver_search.py`](examples/nodriver_search.py) uses this pattern.
- The attempt count and backoff above are a reasonable starting point, not tuned values. If every attempt fails, the cause is usually setup rather than bad luck; see [Troubleshooting](#troubleshooting).
- Keep retries modest; hammering the site won't help and isn't polite.
- A missing `[nodriver]` extra raises `ImportError` when the handler is constructed; that isn't something to retry.

### Performance Testing

The library includes built-in performance testing capabilities with configurable thresholds:

```python
# Configure performance thresholds in pyproject.toml
[tool.performance-thresholds]
unflare_cache_hit_speedup = 10.0  # Cache hits should be 10x faster than misses
direct_request_timeout = 5.0       # Direct requests should timeout within 5s
unflare_first_request_max = 30.0  # First Unflare request max time in seconds
```

Run performance tests:
```bash
# Run performance tests
uv run pytest tests/performance/ -m performance

# Run specific performance tests
uv run pytest tests/performance/handlers/test_unflare_performance.py::test_unflare_cache_speedup
```

## Troubleshooting

### Common Issues

#### "Connection refused" or "Service unavailable" errors
- **Cause**: Unflare service is not running
- **Solution**: 
  1. Ensure you've installed Unflare: [https://github.com/iamyegor/Unflare](https://github.com/iamyegor/Unflare)
  2. Start the Unflare service (usually `http://localhost:5002`)
  3. Verify the service is accessible: `curl http://localhost:5002/health` (if available)

#### `RuntimeError: asyncio.run() cannot be called from a running event loop`
- **Cause**: calling `asyncio.run(...)` inside a Jupyter notebook (or other code that is already running async code).
- **Solution**: in a notebook, `await` the function directly in the cell, e.g. `df = await search_transactions()`. See [Running the examples in Jupyter](#running-the-examples-in-jupyter).

#### Empty results with `errors: ["ValueError('No response from the request handler')"]`
- **Cause**: The request handler couldn't fetch the page: direct requests blocked by Cloudflare, or a bypass handler couldn't clear the challenge (for Unflare, the service may also be down)
- **Solution**: Use a bypass handler — `NodriverRequestHandler` or `UnflareRequestHandler` — instead of default direct requests. If you already do and this appears only occasionally, retry; an occasional failed solve is normal. See [Handling failures and retries](#handling-failures-and-retries)

#### nodriver: request returns `None` / challenge never clears
- **Occasional failure**: a single failed solve can happen; retry it (see [Handling failures and retries](#handling-failures-and-retries)). The causes below apply when it fails consistently.
- **Which browser launched?** Google Chrome is the only browser verified to clear the challenge; Playwright's bundled Chromium failed in testing. If Chromium is installed alongside Chrome, auto-detect may pick Chromium (it prefers the shortest path), so set `NodriverConfig(browser_executable_path=...)` to your Chrome binary. If you're using Edge, Brave, or another untested browser and it never clears, try Chrome. See [Supported browsers](#supported-browsers).
- **Changed IP / VPN**: a cached session issued to one IP may be rejected from another; the handler then re-solves automatically, which costs another browser launch.
- **Headless host**: run under a virtual display (`xvfb-run -a ...`); headless mode does not reliably solve the managed challenge.
- **opencv can't load**: `verify_cf()` imports `opencv-python` (installed by the extra) to find the Turnstile checkbox. If it can't load, the checkbox is never clicked. On minimal Linux images it needs the system `libgl1` package. Check with `python -c "import cv2"`.

#### nodriver: `ImportError: NodriverRequestHandler requires the 'nodriver' extra...`
- **Cause**: the `nodriver` package isn't installed. `NodriverRequestHandler()` checks at construction so the problem surfaces immediately rather than as an empty result.
- **Solution**: `pip install pro_sports_transactions[nodriver]`.

#### nodriver: `RuntimeError: Event loop is closed` at exit
- **Harmless**: nodriver's browser-teardown callbacks can fire after the event loop has shut down. Results are unaffected.

#### Slow performance on first request
- **Expected**: The first request takes longer as it clears Cloudflare (a browser solve for nodriver, or a service round-trip for Unflare)
- **Optimization**: Subsequent requests reuse the cached `cf_clearance` session and are much faster

### Getting Help
- **nodriver Setup Issues**: See the [nodriver docs](https://github.com/ultrafunkamsterdam/nodriver) and [`docs/nodriver/README.md`](docs/nodriver/README.md)
- **Unflare Setup Issues**: See [Unflare documentation](https://github.com/iamyegor/Unflare)
- **Library Issues**: Open an issue on this repository
## Results
```
# DataFrame
print(df)

# returns
          Date    Team        Acquired    Relinquished                                     Notes
0   2022-11-10  Lakers                  • LeBron James  placed on IL with strained left adductor
1   2022-11-25  Lakers  • LeBron James                                         activated from IL
2   2022-12-07  Lakers                  • LeBron James         placed on IL with sore left ankle
3   2022-12-09  Lakers  • LeBron James                                         activated from IL
4   2022-12-19  Lakers                  • LeBron James         placed on IL with sore left ankle
5   2022-12-21  Lakers  • LeBron James                                         activated from IL
6   2023-01-09  Lakers                  • LeBron James         placed on IL with sore left ankle
7   2023-01-12  Lakers  • LeBron James                                         activated from IL
8   2023-02-09  Lakers                  • LeBron James         placed on IL with sore left ankle
9   2023-02-15  Lakers  • LeBron James                                         activated from IL
10  2023-02-27  Lakers                  • LeBron James       placed on IL with right foot injury
11  2023-03-26  Lakers  • LeBron James                                         activated from IL

# Pages
print(df.attrs["pages])

# returns
1

```

# Testing

The library includes comprehensive test suites with different categories:

## Running Tests
```bash
# Run all unit tests (default)
uv run pytest

# Run integration tests (requires external services)
uv run pytest tests/integration/ -m integration

# Run performance tests
uv run pytest tests/performance/ -m performance

# Run all tests
uv run pytest tests/ -m "unit or integration or performance"

# Run tests with coverage
uv run pytest --cov=src/pro_sports_transactions
```

## Test Categories
- **Unit Tests**: Fast, isolated tests of individual components
- **Integration Tests**: Tests requiring external services (may be skipped if services unavailable)
- **Performance Tests**: Benchmarks with configurable thresholds from `pyproject.toml`

# Development

This project uses [uv](https://docs.astral.sh/uv/) for dependency management and
[Ruff](https://docs.astral.sh/ruff/) for formatting and linting.

## Code Quality
The project maintains high code quality standards:

```bash
# Format code
uv run ruff format .

# Lint (and auto-fix where possible)
uv run ruff check --fix .
```

## Contributing
1. Install dependencies: `uv sync --group dev`
2. Run tests: `uv run pytest`
3. Format code: `uv run ruff format .`
4. Lint code: `uv run ruff check .`

Pull request titles must follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) —
see [CONTRIBUTING.md](CONTRIBUTING.md).

# Requirements
Pro Sports Transactions presents data in an HTML table. To make retrieval easy, [`pandas.read_html`](https://pandas.pydata.org/docs/reference/api/pandas.read_html.html) is used which in turn results in additional depencies. The following are a list of required libraries: 

## Runtime Dependencies
- python >=3.11
- aiohttp >=3.13.3,<4
- pandas >=2.2.2,<4
- brotli >=1.2.0,<2
- lxml >=4.9.2,<7.0.0
- html5lib >=1.1,<2
- bs4 >=0.0.1,<0.0.2

## Optional Dependencies (`nodriver` extra)
Install with `pip install pro_sports_transactions[nodriver]` to use `NodriverRequestHandler`:
- nodriver >=0.50,<1
- opencv-python >=4.9,<5

Also required, but not pip-installable: a **Chromium-based browser** (Google Chrome is the tested, recommended choice; see [Supported browsers](#supported-browsers)), and a virtual display (e.g. `xvfb`) on headless hosts.

## Development Dependencies
- pytest >=9.0,<10
- pytest-asyncio >=1.3,<2
- pytest-mock >=3.14,<4
- ruff >=0.15.4

&nbsp;
# Thank You Frank Marousek!
Huge thanks to Frank Marousek @ Pro Sports Transactions for all of his efforts, and the efforts of those who have helped him, in compiling an excellent source of transactional information.
  
&nbsp;
# Disclaimer on accuracy, usage, and completeness of information.
The Pro Sports Transactions API is in no way affiliated with [Pro Sports Transactions](https://www.prosportstransactions.com/). The Pro Sports Transactions API provides a means for programatic access to [Pro Sports Transactions](https://www.prosportstransactions.com/). While the The Pro Sports Transactions API is open source under an MIT License, usage of all information obtained via the Pro Sports Transactions API is subject to all rights reserved by [Pro Sports Transactions](https://www.prosportstransactions.com/). No warranty, express or implied, is made regarding accuracy, adequacy, completeness, legality, reliability or usefulness of any information.

For questions, concerns, or other regarding the information provided via the Pro Sports Transaction API, please visit [Pro Sports Transactions](https://www.prosportstransactions.com/).