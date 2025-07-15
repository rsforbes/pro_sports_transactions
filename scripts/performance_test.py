#!/usr/bin/env python3
"""
Performance testing script for Pro Sports Transactions API.
Measures connection times, Cloudflare bypass, and page loading times.
"""

import asyncio
import time
from datetime import date, timedelta
from typing import Dict, List, Optional
import sys
import os

from pro_sports_transactions.search import Search, League, TransactionType
from pro_sports_transactions.simple_playwright import SimplePlaywrightClient

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class PerformanceMetrics:
    """Track performance metrics for each request"""

    def __init__(self):
        self.initial_connection_time: Optional[float] = None
        self.cloudflare_bypass_time: Optional[float] = None
        self.page_load_times: List[Dict[str, float]] = []
        self.cloudflare_encountered_per_page: List[bool] = []
        self.session_reused: List[bool] = []

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for reporting"""
        return {
            "initial_connection_time": self.initial_connection_time,
            "cloudflare_bypass_time": self.cloudflare_bypass_time,
            "page_load_times": self.page_load_times,
            "cloudflare_encountered_per_page": self.cloudflare_encountered_per_page,
            "session_reused": self.session_reused,
            "total_pages_loaded": len(self.page_load_times),
        }


class PerformanceTestClient(SimplePlaywrightClient):
    """Extended Playwright client with performance tracking"""

    def __init__(self, browser_type="chromium"):
        super().__init__()
        self.metrics = PerformanceMetrics()
        self.browser = None
        self.context = None
        self.page = None
        self.session_established = False
        self.playwright = None
        self.browser_type = browser_type

    async def initialize_session(self):
        """Initialize browser session for reuse"""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        self.browser, self.context = await self._setup_browser_context_for_type(
            self.playwright
        )
        self.page = await self.context.new_page()

    async def _setup_browser_context_for_type(self, playwright):
        """Set up browser context for specific browser type."""
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        if self.browser_type == "chromium":
            browser = await playwright.chromium.launch(headless=True)
        elif self.browser_type == "firefox":
            browser = await playwright.firefox.launch(headless=True)
        elif self.browser_type == "webkit":
            browser = await playwright.webkit.launch(headless=True)
        else:
            raise ValueError(f"Unknown browser type: {self.browser_type}")

        context = await browser.new_context(user_agent=user_agent)
        return browser, context

    async def close_session(self):
        """Close the browser session"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _navigate_and_wait_with_metrics(self, url: str, page_number: int):
        """Navigate to page and track performance metrics"""
        start_time = time.time()
        cloudflare_encountered = False

        # Check cookies before navigation
        cookies_before = await self.context.cookies()
        cf_cookies_before = [c for c in cookies_before if "cf" in c["name"].lower()]

        # Navigate to the page
        await self.page.goto(url, wait_until="networkidle", timeout=60000)
        navigation_time = time.time() - start_time

        # Check for Cloudflare
        title = await self.page.title()
        if "just a moment" in title.lower():
            cloudflare_encountered = True
            cloudflare_start = time.time()

            await asyncio.sleep(10)
            try:
                await self.page.wait_for_function(
                    "() => !document.title.toLowerCase().includes('just a moment')",
                    timeout=30000,
                )
            except Exception:
                pass

            cloudflare_time = time.time() - cloudflare_start

            # Record Cloudflare bypass time for first page only
            if page_number == 1 and self.metrics.cloudflare_bypass_time is None:
                self.metrics.cloudflare_bypass_time = cloudflare_time
        else:
            await asyncio.sleep(2)  # Standard wait time

        # Check cookies after navigation
        cookies_after = await self.context.cookies()
        cf_cookies_after = [c for c in cookies_after if "cf" in c["name"].lower()]

        # Debug cookie persistence
        if page_number == 1 or cloudflare_encountered:
            print(f"    - Cloudflare cookies before: {len(cf_cookies_before)}")
            print(f"    - Cloudflare cookies after: {len(cf_cookies_after)}")

        total_time = time.time() - start_time

        # Record metrics
        self.metrics.cloudflare_encountered_per_page.append(cloudflare_encountered)
        self.metrics.page_load_times.append(
            {
                "page": page_number,
                "navigation_time": navigation_time,
                "total_time": total_time,
                "cloudflare_encountered": cloudflare_encountered,
            }
        )

        # Record initial connection time for first page
        if page_number == 1 and self.metrics.initial_connection_time is None:
            self.metrics.initial_connection_time = navigation_time

        # Track session reuse
        self.metrics.session_reused.append(self.session_established)
        self.session_established = True

        return title

    async def load_page_with_metrics(self, url: str, page_number: int) -> Dict:
        """Load a page and collect performance metrics"""
        try:
            title = await self._navigate_and_wait_with_metrics(url, page_number)

            # Extract transactions
            transactions = []
            pages = 0

            try:
                tables = await self.page.query_selector_all("table")
                transactions, pages = await self._extract_table_data(tables)
            except Exception as e:
                print(f"Error extracting transactions for page {page_number}: {e}")

            return {
                "transactions": transactions,
                "pages": pages,
                "url": url,
                "title": title,
                "page_number": page_number,
            }

        except Exception as e:
            print(f"Error loading page {page_number}: {e}")
            return None


async def check_playwright_browsers(browser_type="chromium"):
    """Check if Playwright browsers are installed"""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Try to launch browser to check if it's installed
            if browser_type == "chromium":
                browser = await p.chromium.launch(headless=True)
            elif browser_type == "firefox":
                browser = await p.firefox.launch(headless=True)
            elif browser_type == "webkit":
                browser = await p.webkit.launch(headless=True)
            else:
                raise ValueError(f"Unknown browser type: {browser_type}")
            await browser.close()
            return True
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            return False
        raise e


async def run_performance_test(browser_type="chromium"):
    """Run the performance test across 5 pages

    Args:
        browser_type: Browser to use - 'chromium', 'firefox', or 'webkit'
    """
    print("Starting Pro Sports Transactions Performance Test")
    print("=" * 60)
    print(f"Browser: {browser_type}")
    print(
        "\n⚠️  NOTE: This test uses session reuse for optimal performance measurement."
    )
    print("The actual search.py creates a NEW browser for each request.")
    print("Run compare_performance.py to see the actual vs optimized behavior.\n")

    # Check if Playwright browsers are installed
    print(f"\nChecking Playwright {browser_type} installation...")
    try:
        if not await check_playwright_browsers(browser_type):
            print(f"\n⚠️  Playwright {browser_type} browser is not installed!")
            print(f"Please run: playwright install {browser_type}")
            print("This is a one-time setup required for all users.")
            print("\nAlternatively, you can use different browsers:")
            print("  - chromium (recommended for consistency)")
            print("  - firefox")
            print("  - webkit (Safari engine)")
            return
    except Exception as e:
        print(f"\n❌ Error checking Playwright installation: {e}")
        return

    # Set up test parameters
    league = League.NBA
    transaction_types = [TransactionType.Movement, TransactionType.InjuredList]
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

    print(f"Test Parameters:")
    print(f"  League: {league.name}")
    print(f"  Transaction Types: {[t.name for t in transaction_types]}")
    print(f"  Date Range: {start_date} to {end_date}")
    print(f"  Pages to test: 5")
    print("=" * 60)

    # Create performance test client
    client = PerformanceTestClient(browser_type)

    try:
        # Initialize session for reuse
        print("\nInitializing browser session...")
        await client.initialize_session()

        # Test 5 pages
        for page_num in range(5):
            print(f"\nLoading page {page_num + 1}...")

            # Create search object for this page
            search = Search(
                league=league,
                transaction_types=transaction_types,
                start_date=start_date,
                end_date=end_date,
                starting_row=page_num * 25,  # Assuming 25 results per page
            )

            # NOTE: This test uses session reuse for performance measurement
            # The actual search.py creates a NEW browser for each request
            # Run compare_performance.py to see the difference

            # Get URL
            url = await search.get_url()

            # Load page with metrics
            result = await client.load_page_with_metrics(url, page_num + 1)

            if result:
                print(f"  ✓ Page {page_num + 1} loaded successfully")
                print(f"    - Transactions found: {len(result['transactions'])}")
                print(f"    - Total pages available: {result['pages']}")

                # Get latest metrics for this page
                page_metrics = client.metrics.page_load_times[-1]
                print(f"    - Navigation time: {page_metrics['navigation_time']:.2f}s")
                print(f"    - Total load time: {page_metrics['total_time']:.2f}s")
                print(
                    f"    - Cloudflare encountered: {page_metrics['cloudflare_encountered']}"
                )
                print(f"    - Session reused: {client.metrics.session_reused[-1]}")
            else:
                print(f"  ✗ Failed to load page {page_num + 1}")

        # Print summary metrics
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)

        metrics = client.metrics.to_dict()

        print(f"\nInitial Connection Time: {metrics['initial_connection_time']:.2f}s")

        if metrics["cloudflare_bypass_time"]:
            print(f"Cloudflare Bypass Time: {metrics['cloudflare_bypass_time']:.2f}s")
        else:
            print("Cloudflare Bypass: Not encountered on initial connection")

        print(f"\nTotal Pages Loaded: {metrics['total_pages_loaded']}")

        # Page load time statistics
        if metrics["page_load_times"]:
            avg_nav_time = sum(
                p["navigation_time"] for p in metrics["page_load_times"]
            ) / len(metrics["page_load_times"])
            avg_total_time = sum(
                p["total_time"] for p in metrics["page_load_times"]
            ) / len(metrics["page_load_times"])

            print(f"\nAverage Navigation Time: {avg_nav_time:.2f}s")
            print(f"Average Total Load Time: {avg_total_time:.2f}s")

            print("\nPer-Page Load Times:")
            for page_data in metrics["page_load_times"]:
                print(
                    f"  Page {page_data['page']}: {page_data['total_time']:.2f}s"
                    + (" (Cloudflare)" if page_data["cloudflare_encountered"] else "")
                )

        # Cloudflare interference analysis
        cloudflare_pages = sum(metrics["cloudflare_encountered_per_page"])
        print(f"\nCloudflare Interference:")
        print(
            f"  Pages with Cloudflare: {cloudflare_pages}/{len(metrics['cloudflare_encountered_per_page'])}"
        )

        if cloudflare_pages > 0:
            if cloudflare_pages == 1:
                print(
                    "  ✓ Cloudflare bypass successful - cookies persisted for subsequent pages"
                )
            else:
                print(
                    "  ⚠️  Cloudflare appeared on multiple pages - cookies may not be persisting"
                )

        # Session reuse analysis
        reused_count = sum(metrics["session_reused"][1:])  # Skip first page
        print(f"\nSession Reuse:")
        print(
            f"  Pages using existing session: {reused_count}/{len(metrics['session_reused']) - 1}"
        )

        if reused_count == len(metrics["session_reused"]) - 1:
            print("  ✓ Same browser session successfully reused for all pages")

    finally:
        # Clean up
        print("\nClosing browser session...")
        await client.close_session()

    print("\nPerformance test completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Performance test for Pro Sports Transactions"
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser to use for testing (default: chromium)",
    )

    args = parser.parse_args()
    asyncio.run(run_performance_test(args.browser))
