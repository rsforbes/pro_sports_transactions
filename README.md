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
- 🚀 **Cloudflare Bypass**: In-process (`NodriverRequestHandler`) or via the Unflare sidecar (`UnflareRequestHandler`)
- 📊 **Multiple Output Formats**: DataFrame, dict, or JSON

## Installation

prosportstransactions.com is protected by a Cloudflare challenge, so direct requests are typically blocked and you'll need a Cloudflare-bypass request handler. The simplest is nodriver, which solves the challenge in-process with a real browser:

```bash
pip install pro_sports_transactions[nodriver]
```

The extra doesn't install a browser: you also need **Google Chrome**, and on a headless Linux host a virtual display such as `xvfb`. See the [nodriver guide](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md#prerequisites) for details, supported browsers, and caveats.

To use the [Unflare](#unflare) service instead, `pip install pro_sports_transactions` is enough. Requires Python 3.11+.

## Quick Start
```python
from datetime import date
import asyncio
import pro_sports_transactions as pst
from pro_sports_transactions.handlers import NodriverRequestHandler


async def search_transactions():
    async with NodriverRequestHandler() as handler:  # closes the browser on exit
        return await pst.Search(
            league=pst.League.NBA,
            transaction_types=tuple(pst.TransactionType),
            start_date=date.fromisoformat("2022-10-18"),
            end_date=date.fromisoformat("2023-04-09"),
            player="LeBron James",
            team="Lakers",
            starting_row=0,  # pagination: the site returns 25 rows per page
            request_handler=handler,  # IMPORTANT: use the bypass handler
        ).get_dataframe()  # Also supports get_dict() and get_json()


if __name__ == "__main__":
    df = asyncio.run(search_transactions())
```

`league` is one of `pst.League.MLB`, `MLS`, `NBA`, `NFL`, or `NHL`. `transaction_types` takes any of `pst.TransactionType.Disciplinary`, `InjuredList`, `Injury`, `LegalIncident`, `MinorLeagueToFrom`, `Movement` (trades, acquisitions, waivers, draft picks, etc.), and `PersonalReason`; `tuple(pst.TransactionType)` searches them all.

On a headless host, run it under `xvfb-run -a python your_script.py`. In Jupyter, see [Async notes](#async-notes).

### Results
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
print(df.attrs["pages"])

# returns
1

```

## Request Handlers

Both bypass handlers do the same thing: a real browser clears the challenge once, and the resulting `cf_clearance` session is cached and replayed over plain HTTP until it expires.

| | `NodriverRequestHandler` | `UnflareRequestHandler` |
| --- | --- | --- |
| Separate service to run | No — in-process | Yes — the Unflare sidecar |
| Extra install footprint | Chromium-based browser (Chrome recommended) + `nodriver` extra + `xvfb` on servers | A running Unflare/Docker service |
| Best when | You want a single `pip install` and no sidecar | You'd rather keep the browser stack out of your app process (e.g. a shared solver container) |

All handlers are used the same way, so switching is a one-line change:

```python
# or UnflareRequestHandler(), DirectRequestHandler()
async with NodriverRequestHandler() as handler:
    df = await pst.Search(..., request_handler=handler).get_dataframe()
```

Reuse one handler across many searches: the first request pays for the solve, later ones replay the cached session. On the bypass handlers, `handler.is_cache_valid()` reports whether a valid session is cached and `handler.has_cached_cookies` whether any cookies are held.

### nodriver

`NodriverRequestHandler` takes an optional `NodriverConfig` and works with its defaults:

```python
from pro_sports_transactions.handlers import NodriverRequestHandler, NodriverConfig

config = NodriverConfig(
    browser_executable_path=None,  # None = auto-detect Chrome/Chromium; or set an explicit path
    headless=False,  # keep False; use xvfb on headless hosts
    verify_attempts=8,  # max Turnstile solve attempts
    solve_timeout=120.0,  # give up on one browser solve after this many seconds
)
handler = NodriverRequestHandler(config)
```

Setup, supported browsers, and caveats are in the [nodriver guide](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md).

### Unflare

1. **Install and run the Unflare service**: follow the setup instructions at [https://github.com/iamyegor/Unflare](https://github.com/iamyegor/Unflare) (it typically runs on `http://localhost:5002`)
2. **Point `UnflareRequestHandler` at it**:

```python
from pro_sports_transactions.handlers import UnflareRequestHandler, UnflareConfig

config = UnflareConfig(
    url="http://localhost:5002/scrape",  # Your Unflare service URL
    timeout=60000,  # Request timeout in milliseconds
    proxy={"host": "proxy.example.com", "port": 8080},  # Optional proxy
)
handler = UnflareRequestHandler(config)
```

### Direct (not recommended)

Direct requests are the **default**: constructing `Search(...)` without a `request_handler` issues a direct request (equivalent to passing `DirectRequestHandler()`). They are typically blocked by Cloudflare; use a bypass handler for reliable access.

## Handling failures and retries

The handlers don't retry failed solves for you; retry policy is left to your application. When a handler can't clear Cloudflare, its `get()` returns `None`, and `Search` does **not** raise. It returns an empty result with the failure recorded in `errors`:

- `get_dataframe()`: an empty DataFrame with `df.attrs["errors"]` set
- `get_dict()` / `get_json()`: an `"errors"` key

An empty result without `errors` means the search genuinely matched nothing. So always check `errors` before trusting an empty result.

Occasional solve failures are expected (the Turnstile check doesn't pass every time), and a retry starts a fresh solve. A request that fails for another reason (a 404, a server error, a timeout, or a persistent network error) also returns `None`, but the handler keeps its cached session, so a retry reuses it. A simple pattern:

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
- Reuse the **same handler** across retries; with nodriver this keeps the browser running, so a retry doesn't pay for another launch. [`examples/nodriver_search.py`](https://github.com/rsforbes/pro_sports_transactions/blob/main/examples/nodriver_search.py) uses this pattern.
- If every attempt fails, the cause is usually setup rather than bad luck; see [Troubleshooting](#troubleshooting). Keep retries modest; hammering the site won't help and isn't polite.
- A missing `[nodriver]` extra raises `ImportError` when the handler is constructed; that isn't something to retry.

## Async notes

The examples use Python's `async` features because fetching web pages involves a lot of waiting:

- `async def` defines a function that can wait without freezing your program.
- `await` runs one of those functions and waits for its result. You can only write `await` inside an `async def` function (or in Jupyter, see below).
- `asyncio.run(...)` starts everything from a normal script.

**In Jupyter**, the notebook already runs an event loop, so `asyncio.run()` fails with `RuntimeError: asyncio.run() cannot be called from a running event loop`. `await` the function directly in a cell instead:

```python
# In a notebook cell, instead of asyncio.run(search_transactions()):
df = await search_transactions()
```

**`async with`** closes the handler when the block ends, even after an error: for nodriver that shuts down the browser, for Unflare it closes its HTTP connections, and for direct it does nothing. You can skip it in a short script, since everything is cleaned up when the script exits. In a notebook or a long-running program, use `async with` or call `await handler.close()` when you're done, or the nodriver browser keeps running in the background.

## Troubleshooting

### Empty results with `errors: ["ValueError('No response from the request handler')"]`
- **Cause**: The request handler couldn't fetch the page: direct requests blocked by Cloudflare, or a bypass handler couldn't clear the challenge (for Unflare, the service may also be down)
- **Solution**: Use a bypass handler — `NodriverRequestHandler` or `UnflareRequestHandler` — instead of default direct requests. If you already do and this appears only occasionally, retry; an occasional failed solve is normal. See [Handling failures and retries](#handling-failures-and-retries)

### "Connection refused" or "Service unavailable" errors
- **Cause**: Unflare service is not running
- **Solution**: Start the Unflare service (usually `http://localhost:5002`); see [Unflare](#unflare)

### Slow first request
- **Expected**: The first request clears Cloudflare (a browser solve for nodriver, or a service round-trip for Unflare). Later requests reuse the cached session and are much faster.

### nodriver issues
- See [Troubleshooting](https://github.com/rsforbes/pro_sports_transactions/blob/main/docs/nodriver.md#troubleshooting) in the nodriver guide, and the [nodriver docs](https://github.com/ultrafunkamsterdam/nodriver).

For anything else, open an issue on this repository.

## Contributing
See [CONTRIBUTING.md](https://github.com/rsforbes/pro_sports_transactions/blob/main/CONTRIBUTING.md) for development setup, tests, and code quality.

&nbsp;
# Thank You Frank Marousek!
Huge thanks to Frank Marousek @ Pro Sports Transactions for all of his efforts, and the efforts of those who have helped him, in compiling an excellent source of transactional information.
  
&nbsp;
# Disclaimer on accuracy, usage, and completeness of information.
The Pro Sports Transactions API is in no way affiliated with [Pro Sports Transactions](https://www.prosportstransactions.com/). The Pro Sports Transactions API provides a means for programatic access to [Pro Sports Transactions](https://www.prosportstransactions.com/). While the The Pro Sports Transactions API is open source under an MIT License, usage of all information obtained via the Pro Sports Transactions API is subject to all rights reserved by [Pro Sports Transactions](https://www.prosportstransactions.com/). No warranty, express or implied, is made regarding accuracy, adequacy, completeness, legality, reliability or usefulness of any information.

For questions, concerns, or other regarding the information provided via the Pro Sports Transaction API, please visit [Pro Sports Transactions](https://www.prosportstransactions.com/).