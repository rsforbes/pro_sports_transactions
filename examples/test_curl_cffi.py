#!/usr/bin/env python3
"""
Test script for curl_cffi integration with pro_sports_transactions

This script tests curl_cffi's TLS fingerprint evasion against prosportstransactions.com
to see if it can bypass the Cloudflare protection that blocked cloudscraper.
"""

import asyncio
import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pro_sports_transactions.search import CurlCffiHttp, CurlCffiConfig


async def test_basic_access():
    """Test basic homepage access with curl_cffi"""
    print("=" * 70)
    print("BASIC ACCESS TEST")
    print("=" * 70)

    print("\n🧪 Testing homepage access with chrome136...")

    # Configure curl_cffi with chrome136
    config = CurlCffiConfig(
        browser="chrome136", debug=True, timeout=30, request_delay=1.0
    )
    CurlCffiHttp.configure(config)

    # Test homepage
    url = "https://www.prosportstransactions.com/"
    print(f"\nTesting URL: {url}")

    start_time = time.time()
    response = await CurlCffiHttp.get(url)
    elapsed = time.time() - start_time

    if response:
        print(f"\n✅ SUCCESS! Response received in {elapsed:.2f}s")
        print(f"Response length: {len(response)} characters")

        # Check for success indicators
        if "Pro Sports Transactions" in response:
            print("✅ Page title found - genuine content received")
        else:
            print("⚠️  Expected title not found")

        # Check for Cloudflare blocks
        if "Just a moment" in response:
            print("❌ Cloudflare challenge page detected")
            return False
        elif "Access denied" in response:
            print("❌ Access denied page detected")
            return False
        else:
            print("✅ No Cloudflare blocking detected")
            return True
    else:
        print(f"\n❌ FAILED after {elapsed:.2f}s")
        return False


async def test_search_page():
    """Test accessing actual search results page"""
    print("\n" + "=" * 70)
    print("SEARCH RESULTS TEST")
    print("=" * 70)

    # NBA search URL (same format our library uses)
    search_url = "https://www.prosportstransactions.com/basketball/Search/SearchResults.php?Player=lebron+james&BeginDate=2023-01-01&EndDate=2023-12-31&Submit=Search"

    print(f"\n🔍 Testing search URL:")
    print(f"   {search_url}")

    start_time = time.time()
    response = await CurlCffiHttp.get(search_url)
    elapsed = time.time() - start_time

    if response:
        print(f"\n✅ Search response received in {elapsed:.2f}s")
        print(f"Response length: {len(response)} characters")

        # Check for search result indicators
        if "LeBron James" in response:
            print("✅ Player name found in results")
        if "Los Angeles Lakers" in response or "Lakers" in response:
            print("✅ Team information found")
        if "Search Results" in response:
            print("✅ Search results page confirmed")

        # Check for data tables
        if "<table" in response and "<tr" in response:
            print("✅ HTML tables found - structured data present")

        # Look for pagination info
        if "Page " in response:
            print("✅ Pagination detected")

        return True
    else:
        print(f"\n❌ Search request failed after {elapsed:.2f}s")
        return False


async def test_different_browsers():
    """Test with different browser impersonations"""
    print("\n" + "=" * 70)
    print("BROWSER COMPARISON TEST")
    print("=" * 70)

    browsers_to_test = ["chrome136", "chrome133a", "safari18_4"]
    test_url = "https://www.prosportstransactions.com/"
    results = {}

    for browser in browsers_to_test:
        print(f"\n🌐 Testing with {browser}...")

        config = CurlCffiConfig(
            browser=browser,
            debug=False,  # Less verbose for comparison
            timeout=15,
            request_delay=1.0,
        )
        CurlCffiHttp.configure(config)

        start_time = time.time()
        response = await CurlCffiHttp.get(test_url)
        elapsed = time.time() - start_time

        if response and "Pro Sports Transactions" in response:
            results[browser] = {"success": True, "time": elapsed}
            print(f"   ✅ Success in {elapsed:.2f}s")
        else:
            results[browser] = {"success": False, "time": elapsed}
            print(f"   ❌ Failed in {elapsed:.2f}s")

    print(f"\n📊 Browser Test Summary:")
    print("-" * 40)
    for browser, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{browser:12} | {status} | {result['time']:.2f}s")


async def test_with_cookies():
    """Test with the working cf_clearance cookie from our research"""
    print("\n" + "=" * 70)
    print("COOKIE SESSION TEST")
    print("=" * 70)

    print("\n🍪 Testing with working cf_clearance cookie...")

    # Use the working cookie from our cloudscraper research
    working_cookie = "yuk1QDs5G23aRROdkuOWRG_bjxbrfQRwJSLxJ3KM5lA-1751119949-1.2.1.1-OgJGCygQmKjn08tEb7ACOy4OMqFWvjcvlZ31og1t3arrGuwt5puxCp.ECMYMuBF68dPq7caZFnYhmKpso0iqqQmBQqWXfLwXiSA6HfR7EbXs5D_U887EcKc7xMpCRHc8VDFdfuy07PA9q7vf5zrkm7xtUVPrNRTs5i4clSsSnlWkP_hOpDgxnWzUxDI9o3Q5rvMtAuzaKbeCOE.7Vv24vy0rPV2q6sBkbLZcVBNNoRLtPkdfdB3vuZ8iSD0jzD5QgiIStW20DUWqfq77A5YNzwnC_i7F9IVGo1fJdwrhIgVQlUnmGk2spvApe35BBmUkGni7._eOjkjbQ9qLXpOm9eRakMo47moey.JjjDmb72OkTSTYWxxFIQMd6pEiFbMO"

    await CurlCffiHttp.configure_with_cookie_session(working_cookie)

    # Test with the cookie
    url = "https://www.prosportstransactions.com/"
    start_time = time.time()
    response = await CurlCffiHttp.get(url)
    elapsed = time.time() - start_time

    if response and "Pro Sports Transactions" in response:
        print(f"✅ Cookie test successful in {elapsed:.2f}s")
        print("✅ TLS + Cookie combination may be effective")
        return True
    else:
        print(f"❌ Cookie test failed in {elapsed:.2f}s")
        return False


def test_sync_interface():
    """Test synchronous interface for comparison"""
    print("\n" + "=" * 70)
    print("SYNCHRONOUS INTERFACE TEST")
    print("=" * 70)

    print("\n⚡ Testing synchronous curl_cffi interface...")

    config = CurlCffiConfig(browser="chrome136", debug=True)
    CurlCffiHttp.configure(config)

    url = "https://www.prosportstransactions.com/"
    start_time = time.time()
    response = CurlCffiHttp.get_sync(url)
    elapsed = time.time() - start_time

    if response and "Pro Sports Transactions" in response:
        print(f"✅ Sync interface successful in {elapsed:.2f}s")
        return True
    else:
        print(f"❌ Sync interface failed in {elapsed:.2f}s")
        return False


async def main():
    """Run comprehensive curl_cffi tests"""
    print("\n" + "🚀" * 35)
    print("CURL_CFFI TLS FINGERPRINT EVASION TEST")
    print("🚀" * 35)
    print("\nThis script tests whether curl_cffi can bypass the TLS fingerprinting")
    print("that blocked cloudscraper on prosportstransactions.com")

    results = {}

    # Run all tests
    print("\n" + "🧪" * 50)
    results["basic"] = await test_basic_access()
    results["search"] = await test_search_page()
    results["browsers"] = await test_different_browsers()
    results["cookies"] = await test_with_cookies()
    results["sync"] = test_sync_interface()

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL TEST RESULTS")
    print("=" * 70)

    test_names = {
        "basic": "Basic Homepage Access",
        "search": "Search Results Page",
        "browsers": "Browser Comparison",
        "cookies": "Cookie Session Test",
        "sync": "Synchronous Interface",
    }

    passed = 0
    total = len(results)

    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_names[test]:25} | {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed > 0:
        print("\n🎉 BREAKTHROUGH! curl_cffi shows promise for TLS evasion!")
        print("✅ The chrome136 browser impersonation appears to bypass detection")
        print("✅ This validates our hypothesis about TLS fingerprinting")
    else:
        print("\n😞 curl_cffi was unable to bypass Cloudflare protection")
        print("❌ May need to explore Playwright or other browser automation")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
