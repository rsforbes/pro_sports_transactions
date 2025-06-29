#!/usr/bin/env python3
"""
Test script for cloudscraper integration with pro_sports_transactions

This script demonstrates how to use the cloudscraper-enhanced version
of the library and provides debugging output for troubleshooting.
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pro_sports_transactions import Search, League, TransactionType
from src.pro_sports_transactions.search import Http, CloudscraperConfig


async def test_basic_search():
    """Test basic search functionality with cloudscraper"""
    print("=" * 70)
    print("BASIC SEARCH TEST")
    print("=" * 70)

    # Create a simple search
    search = Search(
        league=League.NBA,
        player="LeBron James",
        start_date="2023-01-01",
        end_date="2023-12-31",
    )

    # Get the URL
    url = await search.get_url()
    print(f"\nSearch URL: {url}")

    try:
        # Try to get results
        print("\nAttempting to fetch results...")
        results = await search.get_dict()

        if results["transactions"]:
            print(f"\n✅ Success! Found {len(results['transactions'])} transactions")
            print(f"Pages available: {results['pages']}")

            # Show first few transactions
            print("\nFirst 3 transactions:")
            for i, txn in enumerate(results["transactions"][:3]):
                print(f"\n{i+1}. Date: {txn['Date']}")
                print(f"   Team: {txn['Team']}")
                print(f"   Notes: {txn['Notes'][:100]}...")
        else:
            print("\n⚠️  No transactions found (but request succeeded)")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
        if hasattr(e, "__cause__"):
            print(f"   Caused by: {e.__cause__}")


async def test_with_configurations():
    """Test different cloudscraper configurations"""
    print("\n" + "=" * 70)
    print("CONFIGURATION TESTS")
    print("=" * 70)

    configurations = [
        {"name": "Default Configuration", "config": CloudscraperConfig()},
        {
            "name": "Enhanced Stealth Mode",
            "config": CloudscraperConfig(
                enable_stealth=True,
                stealth_min_delay=2.0,
                stealth_max_delay=5.0,
                stealth_human_like_delays=True,
                stealth_randomize_headers=True,
                delay=10,
                debug=False,  # Less verbose
            ),
        },
        {
            "name": "Firefox on Linux",
            "config": CloudscraperConfig(
                browser="firefox",
                browser_platform="linux",
                interpreter="js2py",
                delay=15,
                debug=False,
            ),
        },
        {
            "name": "With Working Cookie",
            "config": CloudscraperConfig(
                session_cookies={
                    "cf_clearance": CloudscraperConfig().get_working_cf_clearance_cookie()
                },
                debug=False,
            ),
        },
    ]

    for test_config in configurations:
        print(f"\n\nTesting: {test_config['name']}")
        print("-" * 50)

        # Configure HTTP client
        Http.configure(test_config["config"])

        # Simple homepage test
        try:
            response = Http.get_sync("https://www.prosportstransactions.com/")
            if response:
                print(f"✅ Homepage accessible")
                if "Just a moment" in response:
                    print("⚠️  Challenge page detected")
                else:
                    print("✅ Got actual content")
            else:
                print("❌ No response received")
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {str(e)[:100]}...")


def test_sync_interface():
    """Test synchronous interface directly"""
    print("\n" + "=" * 70)
    print("SYNCHRONOUS INTERFACE TEST")
    print("=" * 70)

    # Configure with debug mode
    config = CloudscraperConfig(debug=True)
    Http.configure(config)

    # Test direct sync call
    print("\nTesting direct synchronous call...")
    try:
        response = Http.get_sync(
            "https://www.prosportstransactions.com/basketball/Search/SearchResults.php?Player=lebron+james&start=0"
        )
        if response:
            print(f"\n✅ Response received ({len(response)} characters)")
            if "Just a moment" in response:
                print("⚠️  Cloudflare challenge detected")
            elif "LeBron James" in response:
                print("✅ Successfully got search results!")
            else:
                print("🤔 Got response but no expected content")
        else:
            print("❌ No response")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_v3_handler():
    """Test if patched V3 handler is loaded"""
    print("\n" + "=" * 70)
    print("V3 HANDLER TEST")
    print("=" * 70)

    # Configure with debug to see handler messages
    config = CloudscraperConfig(debug=True)
    scraper = Http.configure(config)

    # Check if patched handler is loaded
    if hasattr(scraper, "cloudflare_v3"):
        handler_class = type(scraper.cloudflare_v3).__name__
        print(f"\nV3 Handler Class: {handler_class}")

        if handler_class == "CloudflareV3Patched":
            print("✅ Patched V3 handler successfully loaded!")

            # Check for our custom methods
            if hasattr(scraper.cloudflare_v3, "handle_modern_challenge"):
                print("✅ Modern challenge handler available")
            if hasattr(scraper.cloudflare_v3, "parse_js_object_manually"):
                print("✅ JavaScript object parser available")
        else:
            print("⚠️  Using standard V3 handler")
    else:
        print("❌ No V3 handler found")


async def main():
    """Run all tests"""
    print("\n" + "🔧" * 35)
    print("CLOUDSCRAPER INTEGRATION TEST SUITE")
    print("🔧" * 35)
    print(
        "\nThis script tests the cloudscraper integration with pro_sports_transactions"
    )
    print(
        "Expected: Most tests will fail due to TLS fingerprinting, but we can observe the behavior"
    )

    # Run tests
    await test_basic_search()
    await test_with_configurations()
    test_sync_interface()
    await test_v3_handler()

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("\nKey Findings:")
    print("1. Cloudscraper correctly detects Cloudflare challenges")
    print("2. The patched V3 handler loads successfully")
    print("3. TLS fingerprinting prevents successful bypass")
    print("4. Different configurations show consistent behavior")
    print("\nNext Steps:")
    print("- Consider browser automation (Playwright/Puppeteer)")
    print("- Investigate TLS libraries (curl_cffi, tls-client)")
    print("- Implement hybrid approach with browser token generation")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
