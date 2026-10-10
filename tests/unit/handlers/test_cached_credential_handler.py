"""Unit tests for CachedCredentialHandler: the request/solve decisions of
get(), and how its pieces fit together.

The solve (the subclass hook) and the client are fakes, so only those
decisions are exercised. The pieces have their own tests under
tests/unit/cloudflare/ and tests/unit/concurrency/ (SingleFlight covers
the concurrency mechanics: cancellation, closed event loops).
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from pro_sports_transactions.cloudflare import ReplayResult
from pro_sports_transactions.handlers import (
    CachedCredentialHandler,
    UnflareRequestHandler,
)

URL = "https://www.prosportstransactions.com/basketball/Search/SearchResults.php"
OK = ReplayResult(text="<html>ok</html>")
REJECTED = ReplayResult(rejected=True)
SITE_FAILURE = ReplayResult()


def clearance(value, expires_in=3600):
    return [
        {"name": "cf_clearance", "value": value, "expires": time.time() + expires_in}
    ]


class FakeClient:
    """Answers with ``respond(cookies)`` after a short wait, and records the
    cookies each request carried."""

    def __init__(self, respond=lambda cookies: OK):
        self.respond = respond
        self.sent = []
        self.in_flight = 0
        self.peak = 0

    async def fetch(self, url, request_headers, credential_headers, cookies):
        self.sent.append(cookies)
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        await asyncio.sleep(0.01)
        self.in_flight -= 1
        return self.respond(cookies)

    async def close(self):
        self.closed = True


class CountingHandler(CachedCredentialHandler):
    """A handler whose solve caches new credentials (v1, v2, ...) after a
    short wait, long enough for concurrent callers to queue behind it."""

    def __init__(self, respond=lambda cookies: OK, expires_in=3600):
        super().__init__()
        self.solves = 0
        self.expires_in = expires_in
        self._client = self.client = FakeClient(respond)

    async def _solve(self, url):
        self.solves += 1
        await asyncio.sleep(0.01)
        self.cache_credentials(
            clearance(f"v{self.solves}", self.expires_in), {"User-Agent": "UA"}
        )
        return True


def rejecting(*values):
    """A response rule that rejects the given cf_clearance values."""
    rejected = {f"cf_clearance={v}" for v in values}
    return lambda cookies: REJECTED if cookies in rejected else OK


async def get_many(handler, n=5, **kwargs):
    return await asyncio.gather(*(handler.get(URL, {}) for _ in range(n)), **kwargs)


class TestSingleFlight:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_cold_start_triggers_one_solve(self):
        handler = CountingHandler()

        assert await get_many(handler) == ["<html>ok</html>"] * 5
        assert handler.solves == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_sharing_a_solve_request_in_parallel(self):
        """Only the solve is shared; the requests (each up to the full
        timeout) run at the same time rather than one after another."""
        handler = CountingHandler()

        await get_many(handler)

        assert handler.solves == 1
        assert handler.client.peak == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unflare_concurrent_cold_start_posts_once(self, response, session):
        """Every handler built on the base gets single-flight solving:
        concurrent Unflare callers make one Unflare request."""
        unflare = response(
            json={
                "cookies": [{"name": "cf_clearance", "value": "abc"}],
                "headers": {"User-Agent": "Chrome/154"},
            }
        )
        reply = unflare.json

        async def delayed():
            await asyncio.sleep(0.01)  # long enough for every caller to queue
            return await reply()

        unflare.json = AsyncMock(side_effect=delayed)
        service = session(post=unflare)
        handler = UnflareRequestHandler()
        handler._client = FakeClient()

        with patch("aiohttp.ClientSession", return_value=service):
            results = await get_many(handler)

        assert results == ["<html>ok</html>"] * 5
        assert service.post.call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failed_solve_returns_none_without_requesting(self):
        handler = CountingHandler()
        handler._solve = AsyncMock(return_value=False)

        assert await handler.get(URL, {}) is None
        assert handler.client.sent == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_waiting_on_a_failed_solve_share_its_failure(self):
        """A failed solve fails every caller awaiting it at once, rather than
        each repeating it in turn (the last of N would wait for N solves)."""
        handler = CountingHandler()
        attempts = 0

        async def failing(_url):
            nonlocal attempts
            attempts += 1
            await asyncio.sleep(0.01)
            return False

        handler._solve = failing

        assert await get_many(handler) == [None] * 5
        assert attempts == 1
        assert handler.client.sent == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_waiting_on_a_raising_solve_share_its_exception(self):
        handler = CountingHandler()
        attempts = 0

        async def raising(_url):
            nonlocal attempts
            attempts += 1
            await asyncio.sleep(0.01)
            raise RuntimeError("boom")

        handler._solve = raising

        results = await get_many(handler, return_exceptions=True)

        assert all(isinstance(r, RuntimeError) for r in results)
        assert attempts == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_new_request_after_a_failed_solve_solves_again(self):
        """Sharing applies to callers awaiting the solve: a later request
        (e.g. the caller's retry) gets a fresh attempt."""
        handler = CountingHandler()
        outcomes = [False, True]

        async def solve(url):
            if outcomes.pop(0):
                return await CountingHandler._solve(handler, url)
            return False

        handler._solve = solve

        assert await handler.get(URL, {}) is None
        assert await handler.get(URL, {}) == "<html>ok</html>"
        assert outcomes == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_solve_that_caches_nothing_counts_as_failed(self):
        handler = CountingHandler()
        handler._solve = AsyncMock(return_value=True)

        assert await handler.get(URL, {}) is None
        assert handler.client.sent == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_waiters_use_a_solve_that_is_about_to_expire(self):
        """Credentials inside the early-refresh margin are about to expire, not
        rejected: callers awaiting that solve use them rather than each
        solving again."""
        handler = CountingHandler(expires_in=200)

        assert await get_many(handler) == ["<html>ok</html>"] * 5
        assert handler.solves == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_stops_a_solve_and_waiting_requests_get_none(self):
        """close() stops a solve still running (it could otherwise outlive the
        handler and relaunch a browser); requests awaiting it return None."""
        handler = CountingHandler()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(handler.get(URL, {}), 0.001)
        waiter = asyncio.ensure_future(handler.get(URL, {}))
        await asyncio.sleep(0)  # joined the leftover solve
        task = handler._solves.task

        async with handler:
            pass

        assert task.cancelled()
        assert await waiter is None
        assert not handler.is_cache_valid()
        assert handler.client.closed


class TestRequestDecisions:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_valid_cache_is_used_without_solving(self):
        handler = CountingHandler()
        handler.cache_credentials(clearance("old"), {"User-Agent": "UA"})

        assert await handler.get(URL, {}) == "<html>ok</html>"
        assert handler.solves == 0
        assert handler.client.sent == ["cf_clearance=old"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_request_headers_and_credentials_are_passed_to_the_client(self):
        handler = CountingHandler()
        handler._client = AsyncMock()
        handler._client.fetch = AsyncMock(return_value=OK)
        handler.cache_credentials(clearance("tok"), {"User-Agent": "UA"})

        await handler.get(URL, {"h": "v"})

        handler._client.fetch.assert_awaited_once_with(
            URL, {"h": "v"}, {"User-Agent": "UA"}, "cf_clearance=tok"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_site_failure_keeps_the_cache_and_does_not_solve(self):
        handler = CountingHandler(respond=lambda cookies: SITE_FAILURE)
        handler.cache_credentials(clearance("old"), {"User-Agent": "UA"})

        assert await handler.get(URL, {}) is None
        assert handler.solves == 0
        assert handler.is_cache_valid()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_site_failure_after_a_joined_solve_does_not_solve_again(self):
        """A joined solve's credentials that hit a site failure (not a
        rejection) are kept; a re-solve would hit the same failure."""
        handler = CountingHandler(respond=lambda cookies: SITE_FAILURE)

        assert await get_many(handler) == [None] * 5
        assert handler.solves == 1
        assert handler.is_cache_valid()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rejected_cache_is_cleared_then_solved_and_retried(self):
        handler = CountingHandler(respond=rejecting("old"))
        handler.cache_credentials(clearance("old"), {"User-Agent": "UA"})

        assert await handler.get(URL, {}) == "<html>ok</html>"
        assert handler.solves == 1
        assert handler.client.sent == ["cf_clearance=old", "cf_clearance=v1"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_own_solve_rejected_returns_none_without_solving_again(self):
        """A solve this request started was rejected for it: a second solve
        right away is unlikely to do better, so leave retrying to the caller."""
        handler = CountingHandler(respond=rejecting("v1"))

        assert await handler.get(URL, {}) is None
        assert handler.solves == 1
        assert not handler.is_cache_valid()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_rejected_together_share_one_re_solve(self):
        """Callers that awaited one solve and all saw its credentials
        rejected re-solve once between them, not once each."""
        handler = CountingHandler(respond=rejecting("v1"))

        results = await get_many(handler)

        # The caller that started the rejected solve gives up; the others
        # share one re-solve.
        assert results.count("<html>ok</html>") == 4
        assert handler.solves == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_rejected_by_every_solve_stop_after_two_solves(self):
        """Callers that keep joining each other's rejected solves stop after
        their second, rather than driving a third solve in a row."""
        handler = CountingHandler(respond=rejecting("v1", "v2", "v3"))

        assert await get_many(handler) == [None] * 5
        assert handler.solves == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_newer_credentials_stored_during_a_rejected_request_are_used(
        self,
    ):
        """Credentials another caller stored while this request was rejected
        are used, not cleared or solved over."""
        handler = CountingHandler()
        handler.cache_credentials(clearance("old"), {"User-Agent": "UA"})

        def respond(cookies):
            if cookies == "cf_clearance=old":
                # Another caller's credentials land, then our 403 arrives.
                handler.cache_credentials(clearance("new"), {"User-Agent": "UA"})
                return REJECTED
            return OK

        handler.client.respond = respond

        assert await handler.get(URL, {}) == "<html>ok</html>"
        assert handler.solves == 0
        assert handler.client.sent == ["cf_clearance=old", "cf_clearance=new"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_credentials_cleared_before_the_request_are_skipped(self):
        """If a joined solve's credentials are cleared (another request's 403,
        or clear_cache()) before this request sends them, it moves on rather
        than sending none."""
        handler = CountingHandler()

        async def clear_after_first_solve():
            while handler.solves == 0 or not handler.is_cache_valid():
                await asyncio.sleep(0)
            handler.clear_cache()

        results = await asyncio.gather(
            handler.get(URL, {}), handler.get(URL, {}), clear_after_first_solve()
        )

        assert None not in handler.client.sent  # never sent without credentials
        assert all(r in ("<html>ok</html>", None) for r in results[:2])

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_makes_a_bounded_number_of_requests(self):
        """Even if every request is rejected while newer credentials keep
        arriving, get() stops instead of looping."""
        handler = CountingHandler()
        handler.cache_credentials(clearance("c0"), {"User-Agent": "UA"})

        def always_superseded(cookies):
            handler.cache_credentials(
                clearance(f"c{len(handler.client.sent)}"), {"User-Agent": "UA"}
            )
            return REJECTED

        handler.client.respond = always_superseded

        assert await handler.get(URL, {}) is None
        assert len(handler.client.sent) == 3
        assert handler.solves == 0


class TestSubclassing:
    @pytest.mark.unit
    def test_subclass_without_a_solve_cannot_be_constructed(self):
        class Incomplete(CachedCredentialHandler):
            pass

        with pytest.raises(TypeError, match="_solve"):
            Incomplete()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_rejection_clears_through_an_overridden_clear_cache(self):
        class Tracking(CountingHandler):
            cleared = 0

            def clear_cache(self):
                self.cleared += 1
                super().clear_cache()

        handler = Tracking(respond=rejecting("old"))
        handler.cache_credentials(clearance("old"), {"User-Agent": "UA"})

        assert await handler.get(URL, {}) == "<html>ok</html>"
        assert handler.cleared == 1
