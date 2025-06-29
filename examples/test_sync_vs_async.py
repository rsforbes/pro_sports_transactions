#!/usr/bin/env python3
"""
Test sync vs async curl_cffi behavior
Based on GitHub issue showing differences between sync and async sessions
"""

from curl_cffi import requests as curl_requests
from curl_cffi.requests import AsyncSession
import asyncio


def test_sync():
    print("🧪 Testing SYNC curl_cffi.requests...")
    try:
        response = curl_requests.get(
            "https://www.prosportstransactions.com/",
            impersonate="chrome136",
            timeout=10,
        )
        print(f"Sync Status: {response.status_code}")

        if response.status_code == 200 and "Pro Sports Transactions" in response.text:
            print("✅ Sync: Genuine content received")
            return True
        elif "Just a moment" in response.text or response.status_code == 403:
            print("❌ Sync: Cloudflare challenge/block")
            return False
        else:
            print(f"⚠️  Sync: Unexpected response ({len(response.text)} chars)")
            return False

    except Exception as e:
        print(f"❌ Sync Error: {e}")
        return False


async def test_async():
    print("🧪 Testing ASYNC AsyncSession...")
    try:
        async with AsyncSession(impersonate="chrome136") as session:
            response = await session.get(
                "https://www.prosportstransactions.com/", timeout=10
            )
            print(f"Async Status: {response.status_code}")

            if (
                response.status_code == 200
                and "Pro Sports Transactions" in response.text
            ):
                print("✅ Async: Genuine content received")
                return True
            elif "Just a moment" in response.text or response.status_code == 403:
                print("❌ Async: Cloudflare challenge/block")
                return False
            else:
                print(f"⚠️  Async: Unexpected response ({len(response.text)} chars)")
                return False

    except Exception as e:
        print(f"❌ Async Error: {e}")
        return False


async def test_async_without_impersonate():
    """Test async without impersonate parameter (like the bug report)"""
    print("🧪 Testing ASYNC without impersonate...")
    try:
        async with AsyncSession() as session:  # No impersonate parameter
            response = await session.get(
                "https://www.prosportstransactions.com/", timeout=10
            )
            print(f"Async (no impersonate) Status: {response.status_code}")

            if (
                response.status_code == 200
                and "Pro Sports Transactions" in response.text
            ):
                print("✅ Async (no impersonate): Genuine content received")
                return True
            elif "Just a moment" in response.text or response.status_code == 403:
                print("❌ Async (no impersonate): Cloudflare challenge/block")
                return False
            else:
                print(
                    f"⚠️  Async (no impersonate): Unexpected response ({len(response.text)} chars)"
                )
                return False

    except Exception as e:
        print(f"❌ Async (no impersonate) Error: {e}")
        return False


def test_httpbin_sync():
    """Verify sync impersonation works"""
    print("🧪 Testing SYNC with HttpBin...")
    try:
        response = curl_requests.get(
            "https://httpbin.org/user-agent", impersonate="chrome136"
        )
        user_agent = response.json().get("user-agent", "")
        print(f"Sync User-Agent: {user_agent}")
        return "Chrome/136" in user_agent
    except Exception as e:
        print(f"❌ Sync HttpBin Error: {e}")
        return False


async def test_httpbin_async():
    """Verify async impersonation works"""
    print("🧪 Testing ASYNC with HttpBin...")
    try:
        async with AsyncSession(impersonate="chrome136") as session:
            response = await session.get("https://httpbin.org/user-agent")
            user_agent = response.json().get("user-agent", "")
            print(f"Async User-Agent: {user_agent}")
            return "Chrome/136" in user_agent
    except Exception as e:
        print(f"❌ Async HttpBin Error: {e}")
        return False


async def main():
    print("=" * 70)
    print("SYNC vs ASYNC CURL_CFFI COMPARISON")
    print("=" * 70)
    print("Testing based on GitHub issue about sync/async differences")

    # Test HttpBin first to verify impersonation works
    print("\n--- Verification Tests (HttpBin) ---")
    sync_httpbin = test_httpbin_sync()
    async_httpbin = await test_httpbin_async()

    print(f'Sync HttpBin: {"✅ PASS" if sync_httpbin else "❌ FAIL"}')
    print(f'Async HttpBin: {"✅ PASS" if async_httpbin else "❌ FAIL"}')

    if not sync_httpbin or not async_httpbin:
        print("⚠️  Impersonation not working properly, aborting PST tests")
        return

    # Test ProSportsTransactions
    print("\n--- ProSportsTransactions Tests ---")
    sync_result = test_sync()
    print()
    async_result = await test_async()
    print()
    async_no_impersonate = await test_async_without_impersonate()

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f'Sync (with impersonate):     {"✅ SUCCESS" if sync_result else "❌ FAILED"}')
    print(f'Async (with impersonate):    {"✅ SUCCESS" if async_result else "❌ FAILED"}')
    print(
        f'Async (without impersonate): {"✅ SUCCESS" if async_no_impersonate else "❌ FAILED"}'
    )

    if sync_result != async_result:
        print("\n⚠️  DIFFERENCE DETECTED between sync and async with impersonate!")
        print("This suggests an implementation issue in curl_cffi async sessions")
    elif sync_result == async_result and not sync_result:
        print("\n💡 Sync and async both fail consistently")
        print("ProSportsTransactions blocks both - not a sync/async issue")
    else:
        print("\n✅ Sync and async behavior is consistent")

    if async_result != async_no_impersonate:
        print("\n✅ Impersonate parameter makes a difference in async sessions")
    else:
        print("\n⚠️  Impersonate parameter has no effect in async sessions")


if __name__ == "__main__":
    asyncio.run(main())
