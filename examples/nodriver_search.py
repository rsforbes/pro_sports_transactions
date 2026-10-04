"""Example: Search for NBA transactions using the nodriver handler.

Solves the Cloudflare challenge in-process with a real browser, then
replays the cached session over plain HTTP. No separate service is required.

Requires the nodriver extra and a Chromium-based browser. Google Chrome is the
tested, recommended choice; Edge, Brave, etc. are untested:
    pip install pro_sports_transactions[nodriver]

Usage:
    python examples/nodriver_search.py

On a headless Linux host (server, container, CI), run under a virtual display:
    xvfb-run -a python examples/nodriver_search.py

In a Jupyter notebook, paste the code into a cell and replace
asyncio.run(main()) with: await main()
"""

import asyncio
import calendar
import logging
from datetime import date

from pro_sports_transactions import League, Search, TransactionType
from pro_sports_transactions.handlers import NodriverConfig, NodriverRequestHandler

# Adjust log level to see debug output from the handler:
#   logging.DEBUG  - shows solve attempts and cached-replay decisions
#   logging.INFO   - default, minimal output
#   logging.WARNING - only errors and unexpected status codes
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def get_dataframe_with_retry(search, attempts=3):
    """Retry a search whose solve failed. The handlers don't retry for you: a
    failed Cloudflare solve comes back as an empty DataFrame with
    df.attrs["errors"] set, and each retry gets a fresh solve attempt."""
    df = None
    for attempt in range(attempts):
        df = await search.get_dataframe()
        if "errors" not in df.attrs:
            return df
        if attempt + 1 < attempts:
            print(f"Attempt {attempt + 1} failed: {df.attrs['errors']}; retrying")
            await asyncio.sleep(2**attempt)  # back off: 1s, 2s, ...
    return df


async def main():
    """Search for NBA player movements using the nodriver handler."""
    # None auto-detects Chrome or Chromium. To use another browser (e.g. Edge),
    # or if Chromium is also installed, set the path explicitly - auto-detect
    # may otherwise pick Chromium, which failed in testing. Examples:
    # "/usr/bin/google-chrome-stable" or
    # r"C:\Program Files\Google\Chrome\Application\chrome.exe".
    config = NodriverConfig(browser_executable_path=None)

    # The context manager closes the browser on exit. Reuse one handler for every
    # search so only the first request pays the browser cost.
    async with NodriverRequestHandler(config) as handler:
        for month in (1, 2):
            search = Search(
                league=League.NBA,
                transaction_types=(TransactionType.Movement,),
                start_date=date(2024, month, 1),
                end_date=date(2024, month, calendar.monthrange(2024, month)[1]),
                request_handler=handler,
            )

            print(f"Search URL: {await search.get_url()}")

            # First iteration: the browser solves the challenge (on a desktop a
            # window opens; under xvfb nothing is visible).
            # Second iteration: the cached cf_clearance is replayed over HTTP.
            df = await get_dataframe_with_retry(search)

            if "errors" in df.attrs:
                print(f"Giving up: {df.attrs['errors']}")
                return

            print(f"Found {len(df)} transactions ({df.attrs['pages']} page(s))")
            print(f"Cached session valid: {handler.is_cache_valid()}\n")
            print(df.head().to_string(index=False), "\n")


if __name__ == "__main__":
    asyncio.run(main())
