#!/usr/bin/env python3
"""
Advanced curl_cffi testing with different configurations
Based on GitHub bug reports and curl-impersonate documentation
"""

import asyncio
import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from curl_cffi import requests as curl_requests


def test_basic_curl_cffi():
    """Test basic curl_cffi.requests interface"""
    print("🧪 Test 1: Basic curl_cffi.requests")

    try:
        response = curl_requests.get(
            "https://www.prosportstransactions.com/",
            impersonate="chrome136",
            timeout=10,
        )
        print(f"Status: {response.status_code}")
        return (
            response.status_code == 200 and "Pro Sports Transactions" in response.text
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_no_encoding():
    """Test with disabled Accept-Encoding (based on bug report)"""
    print("\n🧪 Test 2: Disabled Accept-Encoding")

    try:
        response = curl_requests.get(
            "https://www.prosportstransactions.com/",
            impersonate="chrome136",
            headers={"Accept-Encoding": ""},  # Disable encoding
            timeout=10,
        )
        print(f"Status: {response.status_code}")
        return (
            response.status_code == 200 and "Pro Sports Transactions" in response.text
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_manual_headers():
    """Test with manually crafted headers (similar to curl-impersonate wrapper scripts)"""
    print("\n🧪 Test 3: Manual browser headers")

    # Headers from curl-impersonate chrome116 wrapper script approach
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="136", "Google Chrome";v="136"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    }

    try:
        response = curl_requests.get(
            "https://www.prosportstransactions.com/",
            impersonate="chrome136",
            headers=headers,
            timeout=10,
        )
        print(f"Status: {response.status_code}")
        return (
            response.status_code == 200 and "Pro Sports Transactions" in response.text
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_different_browsers():
    """Test different browser impersonations"""
    print("\n🧪 Test 4: Different browsers")

    browsers = ["chrome136", "chrome133a", "safari18_4", "firefox135"]
    results = {}

    for browser in browsers:
        print(f"  Testing {browser}...")
        try:
            response = curl_requests.get(
                "https://www.prosportstransactions.com/", impersonate=browser, timeout=8
            )
            success = (
                response.status_code == 200
                and "Pro Sports Transactions" in response.text
            )
            results[browser] = success
            print(f"    Status: {response.status_code} {'✅' if success else '❌'}")
        except Exception as e:
            results[browser] = False
            print(f"    ❌ Error: {e}")

    return any(results.values())


def test_with_session():
    """Test using a session for connection reuse"""
    print("\n🧪 Test 5: Session with connection reuse")

    try:
        # Create a session
        session = curl_requests.Session(impersonate="chrome136")

        # First request
        response1 = session.get("https://www.prosportstransactions.com/", timeout=10)
        print(f"First request status: {response1.status_code}")

        # Second request (reuse connection)
        time.sleep(1)
        response2 = session.get("https://www.prosportstransactions.com/", timeout=10)
        print(f"Second request status: {response2.status_code}")

        success = (
            response2.status_code == 200 and "Pro Sports Transactions" in response2.text
        )
        return success

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_httpbin_verification():
    """Verify curl_cffi is working correctly with a test service"""
    print("\n🧪 Test 6: HttpBin verification")

    try:
        response = curl_requests.get(
            "https://httpbin.org/user-agent", impersonate="chrome136"
        )
        user_agent_data = response.json()
        print(f"Detected User-Agent: {user_agent_data.get('user-agent', 'None')}")

        # Check if it looks like Chrome
        ua = user_agent_data.get("user-agent", "")
        chrome_detected = "Chrome/136" in ua and "Safari/537.36" in ua
        print(f"Chrome 136 fingerprint: {'✅' if chrome_detected else '❌'}")

        return chrome_detected

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all curl_cffi tests"""
    print("=" * 70)
    print("ADVANCED CURL_CFFI TESTING")
    print("=" * 70)
    print("Testing various curl_cffi configurations based on GitHub issues")
    print("and curl-impersonate documentation")

    tests = [
        ("Basic curl_cffi.requests", test_basic_curl_cffi),
        ("Disabled Accept-Encoding", test_no_encoding),
        ("Manual browser headers", test_manual_headers),
        ("Different browsers", test_different_browsers),
        ("Session reuse", test_with_session),
        ("HttpBin verification", test_httpbin_verification),
    ]

    results = {}
    passed = 0

    for name, test_func in tests:
        print(f"\n{'='*50}")
        try:
            result = test_func()
            results[name] = result
            if result:
                passed += 1
                print(f"✅ {name}: PASSED")
            else:
                print(f"❌ {name}: FAILED")
        except Exception as e:
            results[name] = False
            print(f"❌ {name}: ERROR - {e}")

    print(f"\n{'='*70}")
    print("FINAL RESULTS")
    print(f"{'='*70}")
    print(f"Passed: {passed}/{len(tests)} tests")

    if passed > 0:
        print("\n🎉 Some curl_cffi configurations work!")
        print("This confirms curl_cffi is functional - PST blocking may be solvable")
    else:
        print("\n😞 All curl_cffi tests failed against PST")
        print("ProSportsTransactions likely uses advanced bot detection")

    # Show which tests passed
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:25} | {status}")


if __name__ == "__main__":
    main()
