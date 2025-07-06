#!/usr/bin/env python3
"""
Minimal example demonstrating curl_cffi failing to bypass prosportstransactions.com
JA3/JA4 fingerprinting. This shows why advanced fingerprinting detection is needed.
"""

import json
import sys
from curl_cffi import requests


def test_curl_cffi():
    """Test curl_cffi with various browser impersonations"""
    print("Testing curl_cffi with prosportstransactions.com...")
    print("-" * 60)

    # Target URL
    url = (
        "https://www.prosportstransactions.com/basketball/Search/"
        "SearchResults.php?Player=&Team=&BeginDate=&EndDate="
        "&PlayerMovementChkBx=yes&submit=Search"
    )

    # Try different browser impersonations
    browsers = ["chrome110", "chrome120", "firefox120", "safari17_0"]
    results = []

    for browser in browsers:
        print(f"\n{'='*60}")
        print(f"Testing with {browser} impersonation")
        print(f"{'='*60}")
        try:
            # Create session with browser impersonation
            session = requests.Session(impersonate=browser)

            # Make request
            response = session.get(url, timeout=30, allow_redirects=True)

            # Print detailed response info
            print(f"\nStatus Code: {response.status_code}")
            print(f"URL (after redirects): {response.url}")
            print(f"Content Length: {len(response.content)} bytes")

            # Print response headers
            print("\nResponse Headers:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")

            # Print cookies if any
            if response.cookies:
                print("\nCookies:")
                for cookie in response.cookies:
                    print(f"  {cookie.name}: {cookie.value} (domain: {cookie.domain})")

            # Check if blocked
            if "Checking your browser" in response.text or response.status_code == 403:
                print(f"\n[BLOCKED] Cloudflare challenge detected!")
                results.append((browser, False))
                # Show challenge page content
                print("\nChallenge page preview (first 500 chars):")
                print(response.text[:500])
            else:
                print(f"\n[SUCCESS] Request completed!")
                results.append((browser, True))
                # Show first 300 chars of successful response
                print(f"\nContent preview: {response.text[:300]}...")

        except Exception as e:
            print(f"\n[ERROR] Failed with {browser}: {type(e).__name__}: {e}")
            results.append((browser, False))

    return results


def test_diagnostics():
    """Test with verbose diagnostics to capture request details"""
    print("\n\n" + "=" * 60)
    print("Diagnostic Test - Capturing Request Details")
    print("=" * 60)

    try:
        # Use chrome120 as example
        session = requests.Session(impersonate="chrome120")

        # Test a simpler endpoint first
        print("\nTesting homepage first...")
        response = session.get("https://www.prosportstransactions.com/", timeout=30)

        print(f"Homepage Status: {response.status_code}")
        print(f"Homepage Headers:")
        for k, v in response.headers.items():
            print(f"  {k}: {v}")

        # Check for cf-ray header (Cloudflare indicator)
        if "cf-ray" in response.headers:
            print(f"\nCloudflare Ray ID: {response.headers['cf-ray']}")

        # Check for challenge
        if "Checking your browser" in response.text:
            print("\n[BLOCKED] Homepage also showing challenge")
            # Extract any JavaScript challenge info
            if "window._cf_chl_opt" in response.text:
                print("Cloudflare JavaScript challenge detected")
        else:
            print("\n[SUCCESS] Homepage accessible")

    except Exception as e:
        print(f"\n[ERROR] Diagnostic test failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    # Run tests
    results = test_curl_cffi()
    test_diagnostics()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("Browser impersonation results:")
    for browser, success in results:
        print(f"  {browser}: {'PASSED' if success else 'FAILED'}")

    # Overall result
    any_success = any(success for _, success in results)
    print(
        f"\nOverall: {'At least one method succeeded' if any_success else 'All methods FAILED'}"
    )

    sys.exit(0 if any_success else 1)
