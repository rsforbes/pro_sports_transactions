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

- **`NodriverRequestHandler`** — solves the challenge **in-process** with a real browser (via [nodriver](https://github.com/ultrafunkamsterdam/nodriver)). Enable it with the `nodriver` extra: `pip install pro_sports_transactions[nodriver]`. The extra installs `nodriver` + `opencv-python-headless` only — you also need a Chromium-based browser installed (nodriver uses an existing install; it does not download one). Google Chrome is the tested choice; others are untested (see [Supported browsers](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md#supported-browsers)). On a headless Linux host you also need a virtual display such as `xvfb`. Designed for Windows, macOS, and Linux (live-tested on Linux so far); see [Prerequisites](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md#prerequisites).
- **`UnflareRequestHandler`** — delegates [Unflare](https://github.com/iamyegor/Unflare), a sidecar (container), that you run alongside your app.

Both perform the same underlying bypass (a real browser clears the challenge and hands back a `cf_clearance` session that is cached and replayed). Choose nodriver to avoid running a sidecar, or Unflare to keep the browser stack out of your application process. See [Choosing a handler](#choosing-a-handler).
  
# Getting Started

## Prerequisites

Due to Cloudflare protection, you need a bypass handler. Pick one:

**Option A — nodriver (in-process, no separate service):**

See the [nodriver guide](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md#prerequisites) for the browser, display, and platform requirements.

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
# or UnflareRequestHandler(), DirectRequestHandler()
async with NodriverRequestHandler() as handler:
    df = await pst.Search(..., request_handler=handler).get_dataframe()
```

Each constructor takes an optional config (`NodriverConfig`, `UnflareConfig`) and works with its defaults. `async with` calls `close()` on exit; for nodriver that shuts down the browser and closes the connections its cached-session requests reuse, for Unflare it closes those connections, and for direct it's a no-op, so the same code is correct for every handler.

### nodriver caveats

Know the [nodriver caveats](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md#caveats) before choosing nodriver.

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
# In a notebook cell, instead of asyncio.run(search_transactions()):
df = await search_transactions()
```

### Do I have to use `async with`?

`async with` makes sure the handler cleans up after itself when the block ends, even if an error happens partway through. What "cleaning up" means depends on the handler:

- **nodriver**: shuts down the browser it started, and closes the connections its cached-session requests reuse. The browser is the one that matters.
- **Unflare**: closes the connections its cached-session requests reuse (the Unflare browser runs in its own separate service).
- **direct**: nothing to clean up. `async with` still works, so you can switch handlers without changing your code.

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
# to point at a specific browser. On a headless host, run under xvfb (see the nodriver guide).
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
    # Same pattern as every handler
    async with UnflareRequestHandler(config) as handler:
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
    headless=False,  # keep False; use xvfb on headless hosts
    verify_attempts=8,  # max Turnstile solve attempts
    solve_timeout=120.0,  # give up on one browser solve after this many seconds
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
await handler.close()  # or use `async with handler:` as a context manager
```

#### Unflare Handler (Cloudflare Bypass via Service)
```python
from pro_sports_transactions.handlers import UnflareRequestHandler, UnflareConfig

# Configure the Unflare service connection
# First, set up Unflare: https://github.com/iamyegor/Unflare
config = UnflareConfig(
    url="http://localhost:5002/scrape",  # Your Unflare service URL
    timeout=60000,  # Request timeout in milliseconds
    proxy={"host": "proxy.example.com", "port": 8080},  # Optional proxy
)

handler = UnflareRequestHandler(config)
search = pst.Search(
    league=pst.League.NBA,
    transaction_types=(pst.TransactionType.Movement,),
    request_handler=handler,
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

Occasional solve failures are expected (the Turnstile check doesn't pass every time), and a retry usually starts a fresh attempt: each new request after a failed solve makes the handler load the page again. (Concurrent requests that were waiting on the same solve share its result, so a failed solve fails them together rather than each repeating it.) A request that fails for a reason other than Cloudflare (a 404, a server error, a timeout, or a network error that persists through the handler's short retries) also returns `None`, but the handler keeps its cached session and doesn't solve again, since a fresh session would hit the same failure; a retry reuses the session. A simple pattern:

```python
import asyncio


async def get_dataframe_with_retry(search, attempts=3):
    for attempt in range(attempts):
        df = await search.get_dataframe()
        if "errors" not in df.attrs:
            return df
        if attempt + 1 < attempts:
            await asyncio.sleep(2**attempt)  # back off: 1s, 2s, ...
    return df  # still failing; inspect df.attrs["errors"]


async with NodriverRequestHandler() as handler:
    search = pst.Search(..., request_handler=handler)
    df = await get_dataframe_with_retry(search)
```

Notes:
- Reuse the **same handler** across retries; with nodriver this keeps the browser running, so a retry doesn't pay for another launch (unless the browser itself crashed, in which case the handler relaunches it). [`examples/nodriver_search.py`](https://github.com/rsforbes/pro_sports_transactions/blob/main/examples/nodriver_search.py) uses this pattern.
- The attempt count and backoff above are a reasonable starting point, not tuned values. If every attempt fails, the cause is usually setup rather than bad luck; see [Troubleshooting](#troubleshooting).
- Keep retries modest; hammering the site won't help and isn't polite.
- A missing `[nodriver]` extra raises `ImportError` when the handler is constructed; that isn't something to retry.

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

#### nodriver issues
- See [Troubleshooting](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md#troubleshooting) in the nodriver guide.

#### Slow performance on first request
- **Expected**: The first request takes longer as it clears Cloudflare (a browser solve for nodriver, or a service round-trip for Unflare)
- **Optimization**: Subsequent requests reuse the cached `cf_clearance` session and are much faster

### Getting Help
- **nodriver Setup Issues**: See the [nodriver docs](https://github.com/ultrafunkamsterdam/nodriver) and the [nodriver guide](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md)
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

# Contributing
See [CONTRIBUTING.md](https://github.com/rsforbes/pro_sports_transactions/blob/main/CONTRIBUTING.md) for development setup, tests, and code quality.

# Requirements
Pro Sports Transactions presents data in an HTML table. To make retrieval easy, [`pandas.read_html`](https://pandas.pydata.org/docs/reference/api/pandas.read_html.html) is used which in turn results in additional depencies. The following are a list of required libraries: 

## Runtime Dependencies
- python >=3.11
- aiohttp >=3.14.3,<4
- pandas >=2.2.2,<4
- brotli >=1.2.0,<2
- lxml >=4.9.2,<7.0.0
- html5lib >=1.1,<2
- bs4 >=0.0.1,<0.0.2

## Optional Dependencies (`nodriver` extra)
Install with `pip install pro_sports_transactions[nodriver]` to use `NodriverRequestHandler`:
- nodriver >=0.50,<1
- opencv-python-headless >=4.9,<5

Also required, but not pip-installable: a **Chromium-based browser** (Google Chrome is the tested, recommended choice; see [Supported browsers](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md#supported-browsers)), and a virtual display (e.g. `xvfb`) on headless hosts.

&nbsp;
# Thank You Frank Marousek!
Huge thanks to Frank Marousek @ Pro Sports Transactions for all of his efforts, and the efforts of those who have helped him, in compiling an excellent source of transactional information.
  
&nbsp;
# Disclaimer on accuracy, usage, and completeness of information.
The Pro Sports Transactions API is in no way affiliated with [Pro Sports Transactions](https://www.prosportstransactions.com/). The Pro Sports Transactions API provides a means for programatic access to [Pro Sports Transactions](https://www.prosportstransactions.com/). While the The Pro Sports Transactions API is open source under an MIT License, usage of all information obtained via the Pro Sports Transactions API is subject to all rights reserved by [Pro Sports Transactions](https://www.prosportstransactions.com/). No warranty, express or implied, is made regarding accuracy, adequacy, completeness, legality, reliability or usefulness of any information.

For questions, concerns, or other regarding the information provided via the Pro Sports Transaction API, please visit [Pro Sports Transactions](https://www.prosportstransactions.com/).