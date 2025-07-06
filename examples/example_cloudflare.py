#!/usr/bin/env python3
"""
Minimal example demonstrating cloudscraper with prosportstransactions.com
This example shows the current state of cloudscraper's ability to handle
the site's JA3/JA4 fingerprinting and Cloudflare challenges.
"""

import sys

import cloudscraper


def test_basic_request():
    """Test basic GET request to prosportstransactions.com"""
    print("Testing cloudscraper with prosportstransactions.com...")
    print("-" * 60)

    # Create scraper instance
    scraper = cloudscraper.create_scraper()

    # Target URL
    url = (
        "https://www.prosportstransactions.com/basketball/Search/"
        "SearchResults.php?Player=&Team=&BeginDate=&EndDate="
        "&PlayerMovementChkBx=yes&submit=Search"
    )

    try:
        # Make request
        print(f"Requesting: {url}")
        response = scraper.get(url, timeout=30)

        # Print response details
        print(f"\nStatus Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"\nContent Length: {len(response.content)} bytes")
        print("Content Preview (first 500 chars):")
        print(response.text[:500])

        # Check if we got blocked
        if "Checking your browser" in response.text or response.status_code == 403:
            print("\n[BLOCKED] Cloudflare challenge detected!")
            return False
        print("\n[SUCCESS] Request completed successfully!")
        return True

    except (
        cloudscraper.CloudflareChallengeError,
        Exception,
    ) as e:
        print(f"\n[ERROR] Request failed: {type(e).__name__}: {e}")
        return False


def test_with_browser_params():
    """Test with explicit browser parameters"""
    print("\n\nTesting with browser parameters...")
    print("-" * 60)

    # Create scraper with browser params
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )

    url = "https://www.prosportstransactions.com/"

    try:
        print(f"Requesting: {url}")
        response = scraper.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200 and "Checking your browser" not in response.text:
            print("[SUCCESS] Homepage accessible!")
            return True
        print("[BLOCKED] Still getting challenged")
        return False

    except (
        cloudscraper.CloudflareChallengeError,
        Exception,
    ) as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    # Run tests
    basic_success = test_basic_request()
    browser_success = test_with_browser_params()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Basic request: {'PASSED' if basic_success else 'FAILED'}")
    print(f"Browser params: {'PASSED' if browser_success else 'FAILED'}")

    # Exit with appropriate code
    sys.exit(0 if basic_success or browser_success else 1)
