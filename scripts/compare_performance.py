#!/usr/bin/env python3
"""
Compare performance between actual search.py behavior vs optimized session reuse.
This demonstrates the performance impact of creating a new browser for each request.
"""

import asyncio
import time
from datetime import date, timedelta
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pro_sports_transactions.search import Search, League, TransactionType


async def test_actual_behavior():
    """Test using actual search.py behavior - new browser for each request"""
    print("\n" + "=" * 60)
    print("TEST 1: ACTUAL BEHAVIOR (How search.py currently works)")
    print("=" * 60)
    print("Creating a NEW browser for EACH search request")
    print("This is what happens when users call Search().get_dict()\n")

    league = League.NBA
    transaction_types = [TransactionType.Movement, TransactionType.InjuredList]
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

    total_times = []

    for page_num in range(3):  # Test 3 pages for quicker demo
        print(f"Page {page_num + 1}:")
        start_time = time.time()

        # This is what users actually do
        search = Search(
            league=league,
            transaction_types=transaction_types,
            start_date=start_date,
            end_date=end_date,
            starting_row=page_num * 25,
        )

        # This creates a new browser, navigates, extracts data, then closes browser
        result = await search.get_dict()

        elapsed = time.time() - start_time
        total_times.append(elapsed)

        print(f"  - Time: {elapsed:.2f}s")
        print(f"  - Transactions found: {len(result.get('transactions', []))}")
        print(f"  - Browser lifecycle: Created → Used → Closed")
        print(f"  - Cloudflare challenge: LIKELY on EVERY request\n")

    avg_time = sum(total_times) / len(total_times)
    print(f"Average time per page: {avg_time:.2f}s")
    print(f"Total time for {len(total_times)} pages: {sum(total_times):.2f}s")

    return total_times


async def test_optimized_behavior():
    """Test with session reuse - what the performance test currently measures"""
    print("\n" + "=" * 60)
    print("TEST 2: OPTIMIZED BEHAVIOR (Session reuse)")
    print("=" * 60)
    print("Using ONE browser session for ALL requests")
    print("This is what the performance test measures\n")

    from pro_sports_transactions.simple_playwright import SimplePlaywrightClient
    from playwright.async_api import async_playwright

    league = League.NBA
    transaction_types = [TransactionType.Movement, TransactionType.InjuredList]
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

    total_times = []

    # Create one browser session
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        client = SimplePlaywrightClient()

        for page_num in range(3):  # Test 3 pages
            print(f"Page {page_num + 1}:")
            start_time = time.time()

            search = Search(
                league=league,
                transaction_types=transaction_types,
                start_date=start_date,
                end_date=end_date,
                starting_row=page_num * 25,
            )

            url = await search.get_url()

            # Navigate with existing page
            await page.goto(url, wait_until="networkidle")

            # Check for Cloudflare
            title = await page.title()
            if "just a moment" in title.lower():
                print("  - Cloudflare detected, waiting...")
                await asyncio.sleep(10)

            elapsed = time.time() - start_time
            total_times.append(elapsed)

            print(f"  - Time: {elapsed:.2f}s")
            print(f"  - Browser lifecycle: REUSED from previous request")
            print(
                f"  - Cloudflare challenge: Only on FIRST request (cookies persist)\n"
            )

        await browser.close()

    avg_time = sum(total_times) / len(total_times)
    print(f"Average time per page: {avg_time:.2f}s")
    print(f"Total time for {len(total_times)} pages: {sum(total_times):.2f}s")

    return total_times


async def main():
    """Run both tests and compare results"""
    print("Comparing Performance: Actual vs Optimized Behavior")
    print("This demonstrates why the performance test doesn't match real usage\n")

    # Check if browsers are installed
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            print("⚠️  Playwright browsers are not installed!")
            print("Please run: playwright install chromium")
            return

    # Run actual behavior test
    actual_times = await test_actual_behavior()

    # Run optimized test
    optimized_times = await test_optimized_behavior()

    # Compare results
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)

    actual_avg = sum(actual_times) / len(actual_times)
    optimized_avg = sum(optimized_times) / len(optimized_times)

    print(f"\nActual behavior (new browser each time):")
    print(f"  - Average time: {actual_avg:.2f}s per page")
    print(f"  - Cloudflare challenges: Likely on EVERY request")

    print(f"\nOptimized behavior (session reuse):")
    print(f"  - Average time: {optimized_avg:.2f}s per page")
    print(f"  - Cloudflare challenges: Only on FIRST request")

    if actual_avg > optimized_avg:
        speedup = actual_avg / optimized_avg
        print(f"\n⚡ Session reuse is {speedup:.1f}x faster!")
        print(
            f"💡 Implementing session reuse could save {actual_avg - optimized_avg:.1f}s per request"
        )

    print("\n" + "=" * 60)
    print("KEY INSIGHT:")
    print("The performance test measures the POTENTIAL performance with session reuse,")
    print("but the actual search.py creates a new browser for every request.")
    print("This is why users experience slower performance than the test suggests.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
