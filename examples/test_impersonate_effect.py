#!/usr/bin/env python3
from curl_cffi.requests import AsyncSession
import asyncio


async def test_impersonate_effect():
    print("Testing if impersonate parameter affects async sessions...")

    # Test with impersonate
    async with AsyncSession(impersonate="chrome136") as session:
        response1 = await session.get("https://httpbin.org/headers")
        headers1 = response1.json()

    # Test without impersonate
    async with AsyncSession() as session:
        response2 = await session.get("https://httpbin.org/headers")
        headers2 = response2.json()

    print("Headers WITH impersonate:")
    print(f'  User-Agent: {headers1["headers"].get("User-Agent", "None")}')
    print(f'  Sec-Ch-Ua: {headers1["headers"].get("Sec-Ch-Ua", "None")}')

    print("Headers WITHOUT impersonate:")
    print(f'  User-Agent: {headers2["headers"].get("User-Agent", "None")}')
    print(f'  Sec-Ch-Ua: {headers2["headers"].get("Sec-Ch-Ua", "None")}')

    # Check if they're different
    ua1 = headers1["headers"].get("User-Agent", "")
    ua2 = headers2["headers"].get("User-Agent", "")

    if ua1 != ua2:
        print("✅ Impersonate parameter DOES affect async sessions")
        return True
    else:
        print("❌ Impersonate parameter has NO effect on async sessions")
        return False


asyncio.run(test_impersonate_effect())
