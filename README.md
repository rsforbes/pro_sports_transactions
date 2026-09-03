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

- **`NodriverRequestHandler`** — solves the challenge **in-process** with a real Chrome browser (via [nodriver](https://github.com/ultrafunkamsterdam/nodriver)). Enable it with the `nodriver` extra: `pip install pro_sports_transactions[nodriver]`. The extra installs `nodriver` + `opencv-python` only — you also need Google Chrome present (nodriver uses an existing install; it does not download one) and, on a headless Linux host, a virtual display such as `xvfb`. Works on Windows, macOS, and Linux; see [Prerequisites](#prerequisites).
- **`UnflareRequestHandler`** — delegates [Unflare](https://github.com/iamyegor/Unflare), a sidecar (container), that you run alongside your app.

Both perform the same underlying bypass (a real browser clears the challenge and hands back a `cf_clearance` session that is cached and replayed). Choose nodriver to avoid running a sidecar, or Unflare to keep the browser stack out of your application process. See [Choosing a handler](#choosing-a-handler).
  
# Getting Started

## Prerequisites

Due to Cloudflare protection, you need a bypass handler. Pick one:

**Option A — nodriver (in-process, no separate service):**

Works on **Windows, macOS, and Linux**. Two things are *not* installed for you by pip and must be present:

1. **The library + extra** — `pip install pro_sports_transactions[nodriver]`. This installs `nodriver` and `opencv-python`. It does **not** install a browser.
2. **Google Chrome** — nodriver uses an existing Chrome install rather than downloading one, so make sure Google Chrome (not Chromium) is present. If you already have it, there's nothing to do; otherwise install it:
   - **Windows / macOS**: get Chrome from <https://www.google.com/chrome/>. nodriver auto-detects it (e.g. `C:\Program Files\Google\Chrome\Application\chrome.exe`, `/Applications/Google Chrome.app`).
   - **Linux**: install the `google-chrome-stable` package.
   - If auto-detect picks the wrong binary, set `NodriverConfig(browser_executable_path=r"C:\path\to\chrome.exe")`.
3. **A display** — the browser runs headful.
   - **Windows, macOS, or Linux with a desktop**: nothing extra; it just works.
   - **Headless Linux only** (server, container, CI, WSL without a desktop): install `xvfb` and launch under it, e.g. `xvfb-run -a python your_script.py`. Headless Chrome does not reliably clear the challenge. `xvfb` is Linux-only and is neither needed nor available on Windows/macOS.

**Option B — Unflare (separate service):**

1. **Install and run Unflare service**: Follow the setup instructions at [https://github.com/iamyegor/Unflare](https://github.com/iamyegor/Unflare)
2. **Start the Unflare service** (typically runs on `http://localhost:5002`)
3. **Use `UnflareRequestHandler`** in your code (see examples below)

### Choosing a handler

| | `NodriverRequestHandler` | `UnflareRequestHandler` |
| --- | --- | --- |
| Separate service to run | No — in-process | Yes — the Unflare sidecar |
| Extra install footprint | Chrome + `nodriver` extra + `xvfb` on servers | A running Unflare/Docker service |
| Best when | You want a single `pip install` and no sidecar | You'd rather keep the browser stack out of your app process (e.g. a shared solver container) |

Both cache the `cf_clearance` session after the first solve and replay cheap HTTP requests until it expires.

## Quick Start with nodriver
```python
from datetime import date
import asyncio
import pro_sports_transactions as pst
from pro_sports_transactions.handlers import NodriverRequestHandler, NodriverConfig

# In-process Cloudflare bypass — no separate service required.
# browser_executable_path defaults to auto-detect; set it to point at a
# specific Chrome. On a headless host, run under xvfb (see Prerequisites).
handler = NodriverRequestHandler(NodriverConfig())

async def search_transactions():
    async with handler:  # closes the browser on exit
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
handler = UnflareRequestHandler(config)

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
async def search_transactions() -> str:
    # Search for transactions using Unflare handler
    return await pst.Search(
        league=league,
        transaction_types=transaction_types,
        start_date=start_date,
        end_date=end_date,
        player="LeBron James",
        team="Lakers",
        starting_row=starting_row,
        request_handler=handler  # IMPORTANT: Use Unflare handler
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

# Requires the `nodriver` extra and a real Chrome install:
#   pip install pro_sports_transactions[nodriver]
config = NodriverConfig(
    browser_executable_path=None,  # None = auto-detect Chrome; or set an explicit path
    headless=False,                # keep False; use xvfb on headless hosts
    verify_attempts=8,             # max Turnstile solve attempts
)
handler = NodriverRequestHandler(config)

search = pst.Search(
    league=pst.League.NBA,
    transaction_types=(pst.TransactionType.Movement,),
    request_handler=handler,
)

# The first request drives Chrome to clear the challenge and caches the
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

#### "TypeError: cannot parse from 'NoneType'" errors
- **Cause**: Requests being blocked by Cloudflare (no bypass handler, or the handler could not clear the challenge)
- **Solution**: Use a bypass handler — `NodriverRequestHandler` or `UnflareRequestHandler` — instead of default direct requests

#### nodriver: request returns `None` / challenge never clears
- **Chrome vs Chromium**: nodriver needs a real **Google Chrome**; unbranded Chromium is detected and will not clear the challenge. Set `NodriverConfig(browser_executable_path=...)` if auto-detect picks the wrong binary.
- **Headless host**: run under a virtual display (`xvfb-run -a ...`); headless Chrome does not reliably solve the managed challenge.
- **Missing extra**: ensure you installed `pro_sports_transactions[nodriver]` (it also pulls in `opencv-python`, used to click the Turnstile checkbox).

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

Also required, but not pip-installable: a real **Google Chrome** install, and a virtual display (e.g. `xvfb`) on headless hosts.

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