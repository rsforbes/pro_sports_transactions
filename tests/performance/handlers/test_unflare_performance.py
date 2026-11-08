"""Performance tests for UnflareRequestHandler.

These tests validate performance characteristics including:
1. Cache hit speedup requirements
2. Maximum request timeouts
3. First request completion times

Performance criteria from pyproject.toml:
- unflare_cache_hit_speedup: 10.0x (cache hits should be 10x faster)
- direct_request_timeout: 5.0s (direct requests timeout limit)
- unflare_first_request_max: 30.0s (first unflare request limit)
"""

import time
from datetime import date
from typing import List

import pytest

from pro_sports_transactions.handlers import UnflareRequestHandler
from pro_sports_transactions.search import League, Search, TransactionType

from ..config import get_performance_thresholds

# Load performance thresholds from pyproject.toml
_thresholds = get_performance_thresholds()
UNFLARE_CACHE_HIT_SPEEDUP = _thresholds["unflare_cache_hit_speedup"]
DIRECT_REQUEST_TIMEOUT = _thresholds["direct_request_timeout"]
UNFLARE_FIRST_REQUEST_MAX = _thresholds["unflare_first_request_max"]


async def measure_direct_request_time() -> float:
    """Measure time for a single direct request."""
    start_time = time.perf_counter()
    search = Search(league=League.NBA)
    await search.get_dict()
    return time.perf_counter() - start_time


async def unflare_search(handler: UnflareRequestHandler) -> None:
    """Run one search through Unflare, failing if it didn't fetch a page.

    Search reports a failed fetch in its result rather than raising, so without
    this check a failure would be timed as a (fast) successful request. Searches
    a fixed past range with a transaction type selected: with no type the site
    returns no results table, and Search's default range (today) may be empty.
    """
    result = await Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=date(2023, 1, 1),
        end_date=date(2023, 1, 31),
        request_handler=handler,
    ).get_dict()
    assert "errors" not in result, f"Unflare search failed: {result['errors']}"


async def measure_unflare_requests(
    handler: UnflareRequestHandler, num_requests: int = 3
) -> List[float]:
    """Measure time for multiple Unflare requests using the same handler."""
    times = []
    for _ in range(num_requests):
        start_time = time.perf_counter()
        await unflare_search(handler)
        elapsed_time = time.perf_counter() - start_time
        times.append(elapsed_time)
    return times


async def measure_unflare_first_request(handler: UnflareRequestHandler) -> float:
    """Measure time for first Unflare request (no cache)."""
    # Ensure cache is clear
    handler.clear_cache()
    start_time = time.perf_counter()
    await unflare_search(handler)
    return time.perf_counter() - start_time


@pytest.mark.performance
@pytest.mark.asyncio
async def test_direct_request_timeout():
    """Test that direct requests complete within timeout limit."""
    request_time = await measure_direct_request_time()
    assert request_time < DIRECT_REQUEST_TIMEOUT, (
        f"Direct request took {request_time:.2f}s, "
        f"exceeds limit of {DIRECT_REQUEST_TIMEOUT}s"
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_unflare_first_request_timeout(unflare_config):
    """Test that first Unflare request completes within maximum time."""
    async with UnflareRequestHandler(unflare_config) as handler:
        first_request_time = await measure_unflare_first_request(handler)

    assert first_request_time < UNFLARE_FIRST_REQUEST_MAX, (
        f"First Unflare request took {first_request_time:.2f}s, "
        f"exceeds limit of {UNFLARE_FIRST_REQUEST_MAX}s"
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_unflare_cache_speedup(unflare_config):
    """Test that cached requests are significantly faster than fresh requests."""
    async with UnflareRequestHandler(unflare_config) as handler:
        # Get first request time (populates cache)
        first_request_time = await measure_unflare_first_request(handler)

        # Get subsequent request times (should use cache)
        cached_times = await measure_unflare_requests(handler, num_requests=3)

    cached_avg_time = sum(cached_times) / len(cached_times)

    # Calculate speedup ratio
    speedup_ratio = first_request_time / cached_avg_time

    assert speedup_ratio >= UNFLARE_CACHE_HIT_SPEEDUP, (
        f"Cache speedup is {speedup_ratio:.1f}x, "
        f"below required {UNFLARE_CACHE_HIT_SPEEDUP}x minimum"
    )

    # Additional validation - cached requests should be reasonably fast
    assert cached_avg_time < 5.0, (
        f"Cached requests average {cached_avg_time:.2f}s, should be under 5s"
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_unflare_cache_functionality(unflare_config):
    """Test that cache is working correctly."""
    async with UnflareRequestHandler(unflare_config) as handler:
        # Initially no cache
        assert not handler.has_cached_cookies
        assert handler.cache_expiry_time == 0

        # Make first request to populate cache
        await measure_unflare_first_request(handler)

        # Cache should now be populated
        assert handler.has_cached_cookies
        assert handler.cache_expiry_time > time.time()

        # Cache should be valid
        assert handler.is_cache_valid()

        # Clear cache manually
        handler.clear_cache()
        assert not handler.has_cached_cookies
        assert handler.cache_expiry_time == 0
        assert not handler.is_cache_valid()
