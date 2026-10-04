"""Example: Search for NBA transactions using the Unflare handler.

Requires a running Unflare service (default: http://localhost:5002/scrape).
See https://github.com/iamyegor/Unflare for setup instructions.

Usage:
    python examples/unflare_search.py

In a Jupyter notebook, paste the code into a cell and replace
asyncio.run(main()) with: await main()
"""

import asyncio
import logging
from datetime import date

from pro_sports_transactions import League, Search, TransactionType
from pro_sports_transactions.handlers import UnflareConfig, UnflareRequestHandler

# Adjust log level to see debug output from the handler:
#   logging.DEBUG  - shows fast/slow path decisions
#   logging.INFO   - default, minimal output
#   logging.WARNING - only errors and unexpected status codes
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    """Search for NBA player movements using the Unflare handler."""
    # Configure the Unflare handler
    config = UnflareConfig(
        url="http://localhost:5002/scrape",  # Unflare service URL
        timeout=60000,  # Timeout passed to Unflare (ms)
    )
    # Same calling pattern as every handler: swap in NodriverRequestHandler()
    # or DirectRequestHandler() without changing anything else.
    async with UnflareRequestHandler(config) as handler:
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
