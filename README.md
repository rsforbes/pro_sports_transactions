Pro Sports Transactions API
===============

Pro Sports Transactions is a Python API client-library for https://www.prosportstransactions.com enabling software engineers, data scientists, and sports fans with the ability to easily retrieve trades, free agent movements, signings, injuries, disciplinary actions, legal/criminal actions, and much more for five of the North American professional leagues: MLB, MLS, NBA, NFL, and NHL.

## ⚠️ Important Notice

**Due to Cloudflare protection on prosportstransactions.com, direct requests are typically blocked.** To use this library effectively, you'll need to run the [Unflare service](https://github.com/iamyegor/Unflare) alongside this library and use the `UnflareRequestHandler`.

## Features

- 🏀 **Multi-Sport Support**: MLB, MLS, NBA, NFL, and NHL
- 🚀 **Multiple Request Handlers**: Direct requests or Cloudflare bypass with UnflareRequestHandler
- ⚡ **Performance Testing**: Built-in configurable performance benchmarks
- 🧪 **Comprehensive Testing**: Unit, integration, and performance test suites
- 📊 **Multiple Output Formats**: DataFrame, dict, or JSON
- 🔧 **Configurable**: Performance thresholds and request handling options

&nbsp;
# About
What is sports data without the transactions?
- "Did he just throw his mouthpiece into the stands?"
- "Yep."

`2023-01-27	| Warriors | • Stephen Curry | fined $25,000 by NBA for throwing his mouthpiece into the stands`
  
&nbsp;
# Getting Started

## Prerequisites

**⚠️ Important**: Due to Cloudflare protection, you'll need to set up Unflare before using this library:

1. **Install and run Unflare service**: Follow the setup instructions at [https://github.com/iamyegor/Unflare](https://github.com/iamyegor/Unflare)
2. **Start the Unflare service** (typically runs on `http://localhost:5002`)
3. **Use UnflareRequestHandler** in your code (see examples below)

## Quick Start (Recommended)
```python
from datetime import date
import asyncio
import pro_sports_transactions as pst
from pro_sports_transactions.handlers import UnflareRequestHandler, UnflareConfig

# Configure Unflare handler (REQUIRED for bypassing Cloudflare)
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
# ⚠️ WARNING: Direct requests often fail due to Cloudflare protection
# This example is provided for completeness but may not work reliably

async def search_transactions_direct():
    # Direct usage without handler (likely to be blocked)
    return await pst.Search(
        league=pst.League.NBA,
        transaction_types=tuple([t for t in pst.TransactionType]),
        player="LeBron James"
    ).get_dataframe()
```

## Advanced Usage

### Request Handlers

The library supports different request handlers for various scenarios:

#### Unflare Handler (Recommended - Cloudflare Bypass)
```python
from pro_sports_transactions.handlers import UnflareRequestHandler, UnflareConfig

# Configure Unflare service - REQUIRED for reliable access
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
```python
from pro_sports_transactions.handlers import DirectRequestHandler

# ⚠️ WARNING: Direct requests are typically blocked by Cloudflare
# Use this only for testing or if you have alternative access
handler = DirectRequestHandler()
search = pst.Search(
    league=pst.League.NBA,
    transaction_types=(pst.TransactionType.Movement,),
    request_handler=handler
)
```

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
poetry run pytest tests/performance/ -m performance

# Run specific performance tests
poetry run pytest tests/performance/handlers/test_unflare_performance.py::test_unflare_cache_speedup
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
- **Cause**: Direct requests being blocked by Cloudflare
- **Solution**: Use `UnflareRequestHandler` instead of default direct requests

#### Slow performance on first request
- **Expected**: First Unflare request takes longer as it bypasses Cloudflare
- **Optimization**: Subsequent requests use cached cookies and are much faster

### Getting Help
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
poetry run pytest

# Run integration tests (requires external services)
poetry run pytest tests/integration/ -m integration

# Run performance tests
poetry run pytest tests/performance/ -m performance

# Run all tests
poetry run pytest tests/ -m "unit or integration or performance"

# Run tests with coverage
poetry run pytest --cov=src/pro_sports_transactions
```

## Test Categories
- **Unit Tests**: Fast, isolated tests of individual components
- **Integration Tests**: Tests requiring external services (may be skipped if services unavailable)
- **Performance Tests**: Benchmarks with configurable thresholds from `pyproject.toml`

# Development

## Code Quality
The project maintains high code quality standards:

```bash
# Code formatting
poetry run black .

# Linting (10/10 score maintained)
poetry run pylint .

# Import sorting
poetry run isort .

# Type checking
poetry run flake8
```

## Contributing
1. Install dependencies: `poetry install`
2. Run tests: `poetry run pytest`
3. Ensure pylint score: `poetry run pylint .` (should be 10/10)
4. Format code: `poetry run black .`

# Requirements
Pro Sports Transactions presents data in an HTML table. To make retrieval easy, [`pandas.read_html`](https://pandas.pydata.org/docs/reference/api/pandas.read_html.html) is used which in turn results in additional depencies. The following are a list of required libraries: 

## Runtime Dependencies
- python = "^3.11"
- aiohttp = "^3.8.4"
- pandas = "^2.0.0"
- brotli = "^1.0.9"
- lxml = "^4.9.2"
- html5lib = "^1.1"
- bs4 = "^0.0.1"

## Development Dependencies
- black = "^23.3.0"
- flake8 = "^6.0.0"
- pytest = "^7.3.1"
- pytest-asyncio = "^0.21.0"
- pytest-mock = "^3.10.0"
- isort = "^6.0.1"
- pylint = "^3.3.7"

&nbsp;
# Thank You Frank Marousek!
Huge thanks to Frank Marousek @ Pro Sports Transactions for all of his efforts, and the efforts of those who have helped him, in compiling an excellent source of transactional information.
  
&nbsp;
# Disclaimer on accuracy, usage, and completeness of information.
The Pro Sports Transactions API is in no way affiliated with [Pro Sports Transactions](https://www.prosportstransactions.com/). The Pro Sports Transactions API provides a means for programatic access to [Pro Sports Transactions](https://www.prosportstransactions.com/). While the The Pro Sports Transactions API is open source under an MIT License, usage of all information obtained via the Pro Sports Transactions API is subject to all rights reserved by [Pro Sports Transactions](https://www.prosportstransactions.com/). No warranty, express or implied, is made regarding accuracy, adequacy, completeness, legality, reliability or usefulness of any information.

For questions, concerns, or other regarding the information provided via the Pro Sports Transaction API, please visit [Pro Sports Transactions](https://www.prosportstransactions.com/).