#!/usr/bin/env python3
"""
Usage examples for the pro_sports_transactions library with Playwright JA4 bypass.

This library now uses Playwright by default to bypass Cloudflare protection
on prosportstransactions.com.
"""

import asyncio
from datetime import date, timedelta

from pro_sports_transactions import (
    League,
    TransactionType,
    Search,
    SimplePlaywrightClient,
)


async def basic_search_example():
    """Example of basic search functionality using Playwright"""
    print("=== Basic Search Example ===")

    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=date.today() - timedelta(days=7),
        end_date=date.today(),
    )

    try:
        data = await search.get_dict()
        print(f"Found {len(data['transactions'])} transactions")
        print(f"Total pages: {data['pages']}")

        if data["transactions"]:
            print("Sample transaction:")
            print(data["transactions"][0])
    except Exception as e:
        print(f"Error: {e}")


async def player_search_example():
    """Example of searching for a specific player"""
    print("\n=== Player Search Example ===")

    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement, TransactionType.InjuredList),
        start_date=date.fromisoformat("2023-01-01"),
        end_date=date.fromisoformat("2023-12-31"),
        player="LeBron James",
    )

    try:
        data = await search.get_dict()
        print(f"Found {len(data['transactions'])} LeBron James transactions")

        if data["transactions"]:
            for transaction in data["transactions"][:3]:  # Show first 3
                print(f"  {transaction['Date']}: {transaction['Notes']}")
    except Exception as e:
        print(f"Error: {e}")


def _print_transaction_info(transaction):
    """Helper to print transaction information."""
    acquired = transaction.get("Acquired", "")
    relinquished = transaction.get("Relinquished", "")
    if acquired:
        print(f"  Acquired: {acquired}")
    if relinquished:
        print(f"  Released: {relinquished}")


async def team_search_example():
    """Example of searching for team transactions"""
    print("\n=== Team Search Example ===")

    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=date.fromisoformat("2023-02-01"),
        end_date=date.fromisoformat("2023-02-28"),  # Trade deadline period
        team="Lakers",
    )

    try:
        data = await search.get_dict()
        print(f"Found {len(data['transactions'])} Lakers transactions in Feb 2023")

        if data["transactions"]:
            for transaction in data["transactions"]:
                _print_transaction_info(transaction)
    except Exception as e:
        print(f"Error: {e}")


async def direct_playwright_example():
    """Example of using SimplePlaywrightClient directly"""
    print("\n=== Direct Playwright Client Example ===")

    client = SimplePlaywrightClient()

    # Build URL for NBA movement transactions
    url = (
        "https://www.prosportstransactions.com/basketball/Search/SearchResults.php"
        "?Player=&Team=&BeginDate=&EndDate=&PlayerMovementChkBx=yes&Submit=Search"
    )

    try:
        result = await client.extract_transactions(url)
        print(f"Page title: {result['title']}")
        print(f"Found {len(result['transactions'])} transactions")
        print(f"Total pages: {result['pages']}")

        if result["transactions"]:
            print("Sample transaction:")
            print(result["transactions"][0])

    except Exception as e:
        print(f"Error: {e}")


async def json_output_example():
    """Example of getting JSON output"""
    print("\n=== JSON Output Example ===")

    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=date.today() - timedelta(days=3),
        end_date=date.today(),
    )

    try:
        json_data = await search.get_json()
        print(f"JSON output length: {len(json_data)} characters")
        print("First 200 characters:")
        print(json_data[:200] + "...")

    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run all examples"""
    print("Pro Sports Transactions Library - Usage Examples")
    print("=" * 50)
    print("All requests now use Playwright to bypass Cloudflare protection")
    print("=" * 50)

    await basic_search_example()
    await player_search_example()
    await team_search_example()
    await direct_playwright_example()
    await json_output_example()

    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nNote: All searches automatically use Playwright for JA4 bypass")
    print(
        (
            "No additional configuration needed - "
            + "Cloudflare protection is handled automatically"
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
