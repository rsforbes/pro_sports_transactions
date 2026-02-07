"""Example: Search for NBA transactions using the Cloudscraper handler.

Uses the cloudscraper library to bypass Cloudflare protection locally,
without requiring any external services.

Usage:
    python examples/cloudscraper_search.py
"""

import asyncio
import logging
from datetime import date

from pro_sports_transactions import League, Search, TransactionType
from pro_sports_transactions.handlers import (CloudscraperConfig,
                                              CloudscraperRequestHandler)

# Adjust log level to see debug output from the handler:
#   logging.DEBUG  - shows detailed request info
#   logging.INFO   - default, minimal output
#   logging.WARNING - only errors and unexpected status codes
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    """Search for NBA player movements using the Cloudscraper handler."""
    # Configure the Cloudscraper handler
    config = CloudscraperConfig(
        browser="chrome",  # Browser to emulate (chrome or firefox)
        delay=5,  # Delay for Cloudflare challenges (seconds)
    )
    handler = CloudscraperRequestHandler(config)

    # Search for NBA player movements in a date range
    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        request_handler=handler,
    )

    print(f"Search URL: {await search.get_url()}\n")

    # Get results as a DataFrame
    df = await search.get_dataframe()

    if "errors" in df.attrs:
        print(f"Errors: {df.attrs['errors']}")
        return

    print(f"Found {len(df)} transactions ({df.attrs['pages']} page(s) available)\n")
    print(df.to_string(index=False))


if __name__ == "__main__":
    asyncio.run(main())
