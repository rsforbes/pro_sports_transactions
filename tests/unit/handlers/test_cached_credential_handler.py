"""Unit tests for the shared CachedCredentialHandler orchestration.

Single-flight solving and the replay/solve decisions of get(). The replay
itself is replaced where it would hit the network, so only those decisions are
exercised; the replay is tested through the handlers that use it.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pro_sports_transactions.handlers import (
    CachedCredentialHandler,
    UnflareRequestHandler,
)

URL = "https://www.prosportstransactions.com/basketball/Search/SearchResults.php"


def clearance(value, expires_in=3600):
    return [
        {"name": "cf_clearance", "value": value, "expires": time.time() + expires_in}
    ]


class CountingHandler(CachedCredentialHandler):
    """A handler whose solve caches a new credential (v1, v2, ...) after a
    short wait, long enough for concurrent callers to queue behind it."""

    def __init__(self):
        super().__init__()
        self.solves = 0

    async def _solve(self, url):
        self.solves += 1
        await asyncio.sleep(0.01)
        self.cache_credentials(clearance(f"v{self.solves}"), {"User-Agent": "UA"})
        return True


def reject(handler, *values):
    """A replay that rejects the given cf_clearance values (as a 403 does:
    clearing the cache if it still holds them) and accepts any other."""

    async def replay(_url, _headers):
        # Snapshot what is sent, as the real replay does.
        sent_cookies = handler._cached_cookies
        sent_generation = handler._cache_generation
        await asyncio.sleep(0.01)
        if sent_cookies in {f"cf_clearance={v}" for v in values}:
            if handler._cache_generation == sent_generation:
                handler.clear_cache()
            return None
        return "<html>ok</html>"

    return AsyncMock(side_effect=replay)


class TestSingleFlight:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_cold_start_triggers_one_solve(self):
        handler = CountingHandler()
        handler._try_cached_request = AsyncMock(return_value="<html>ok</html>")

        results = await asyncio.gather(*(handler.get(URL, {}) for _ in range(5)))

        assert results == ["<html>ok</html>"] * 5
        assert handler.solves == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_sharing_a_solve_replay_in_parallel(self):
        """Only the solve is shared; the replays (each up to the full request
        timeout) run at the same time rather than one after another."""
        handler = CountingHandler()
        in_flight = 0
        peak = 0

        async def slow_replay(_url, _headers):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return "<html>ok</html>"

        handler._try_cached_request = AsyncMock(side_effect=slow_replay)

        results = await asyncio.gather(*(handler.get(URL, {}) for _ in range(5)))

        assert results == ["<html>ok</html>"] * 5
        assert handler.solves == 1
        assert peak == 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unflare_concurrent_cold_start_posts_once(self):
        """Every handler built on the base gets single-flight solving, not
        just nodriver: concurrent Unflare callers make one Unflare request."""
        handler = UnflareRequestHandler()

        async def unflare_json():
            await asyncio.sleep(0.01)  # long enough for every caller to queue
            return {
                "cookies": [{"name": "cf_clearance", "value": "abc"}],
                "headers": {"User-Agent": "Chrome/154"},
            }

        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(side_effect=unflare_json)
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=False)
        session = AsyncMock()
        session.post = MagicMock(return_value=response)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        handler._try_cached_request = AsyncMock(return_value="<html>ok</html>")

        with patch("aiohttp.ClientSession", return_value=session):
            results = await asyncio.gather(*(handler.get(URL, {}) for _ in range(5)))

        assert results == ["<html>ok</html>"] * 5
        assert session.post.call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failed_solve_returns_none_without_replaying(self):
        handler = CountingHandler()
        handler._solve = AsyncMock(return_value=False)
        handler._try_cached_request = AsyncMock()

        assert await handler.get(URL, {}) is None
        handler._try_cached_request.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_waiting_on_a_failed_solve_share_its_failure(self):
        """A failed solve fails every caller awaiting it at once, rather than
        each repeating it in turn (the last of N would wait for N solves)."""
        handler = CountingHandler()
        attempts = 0

        async def failing_solve(_url):
            nonlocal attempts
            attempts += 1
            await asyncio.sleep(0.01)
            return False

        handler._solve = failing_solve
        handler._try_cached_request = AsyncMock()

        results = await asyncio.gather(*(handler.get(URL, {}) for _ in range(5)))

        assert results == [None] * 5
        assert attempts == 1
        handler._try_cached_request.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_waiting_on_a_raising_solve_share_its_exception(self):
        handler = CountingHandler()
        attempts = 0

        async def raising_solve(_url):
            nonlocal attempts
            attempts += 1
            await asyncio.sleep(0.01)
            raise RuntimeError("boom")

        handler._solve = raising_solve

        results = await asyncio.gather(
            *(handler.get(URL, {}) for _ in range(5)), return_exceptions=True
        )

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
        handler._try_cached_request = AsyncMock(return_value="<html>ok</html>")

        assert await handler.get(URL, {}) is None
        assert await handler.get(URL, {}) == "<html>ok</html>"
        assert outcomes == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancelling_one_caller_does_not_cancel_the_shared_solve(self):
        handler = CountingHandler()
        handler._try_cached_request = AsyncMock(return_value="<html>ok</html>")

        first = asyncio.ensure_future(handler.get(URL, {}))
        second = asyncio.ensure_future(handler.get(URL, {}))
        await asyncio.sleep(0)  # both are now awaiting the one solve
        first.cancel()

        assert await second == "<html>ok</html>"
        assert first.cancelled()
        assert handler.solves == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_waiters_replay_a_solve_that_is_about_to_expire(self):
        """Credentials inside the 5-minute early-refresh margin are about to
        expire, not rejected: callers awaiting that solve replay them rather
        than each solving again."""
        handler = CountingHandler()

        async def short_lived_solve(_url):
            handler.solves += 1
            await asyncio.sleep(0.01)
            handler.cache_credentials(clearance("v", expires_in=200), {})
            return True

        handler._solve = short_lived_solve
        handler._try_cached_request = AsyncMock(return_value="<html>ok</html>")

        results = await asyncio.gather(*(handler.get(URL, {}) for _ in range(5)))

        assert results == ["<html>ok</html>"] * 5
        assert handler.solves == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_solve_that_caches_nothing_counts_as_failed(self):
        handler = CountingHandler()
        handler._solve = AsyncMock(return_value=True)
        handler._try_cached_request = AsyncMock()

        assert await handler.get(URL, {}) is None
        handler._try_cached_request.assert_not_called()

    @pytest.mark.unit
    def test_a_new_event_loop_does_not_join_a_solve_from_a_closed_one(self):
        """One handler across asyncio.run() calls: a solve task left from an
        earlier (closed) loop must not be awaited by the next."""
        handler = CountingHandler()
        handler._try_cached_request = AsyncMock(return_value="<html>ok</html>")

        async def interrupted():
            asyncio.ensure_future(handler.get(URL, {}))
            await asyncio.sleep(0)  # the solve task has started

        # Close the loop with the solve still pending (asyncio.run() would
        # cancel it, which clears the solve task and skips the loop check).
        old_loop = asyncio.new_event_loop()
        old_loop.run_until_complete(interrupted())
        old_loop.close()
        stale = handler._solve_task
        assert stale is not None and not stale.done()

        assert asyncio.run(handler.get(URL, {})) == "<html>ok</html>"
        assert handler.solves == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_cancels_a_solve_left_by_a_cancelled_request(self):
        """The solve is shielded from its callers, so close() must stop it:
        otherwise it outlives the handler (and could relaunch a browser)."""
        handler = CountingHandler()
        handler._try_cached_request = AsyncMock(return_value="<html>ok</html>")

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(handler.get(URL, {}), 0.001)
        waiter = asyncio.ensure_future(handler.get(URL, {}))
        await asyncio.sleep(0)  # joined the leftover solve
        task = handler._solve_task

        await handler.close()

        assert task.cancelled()
        assert await waiter is None  # a cancelled solve is a failed solve
        assert not handler.is_cache_valid()


class TestReplayDecisions:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_site_failure_keeps_the_cache_and_does_not_solve(self):
        handler = CountingHandler()
        handler.cache_credentials(clearance("old"), {"User-Agent": "UA"})
        handler._try_cached_request = AsyncMock(return_value=None)

        assert await handler.get(URL, {}) is None
        assert handler.solves == 0
        assert handler.is_cache_valid()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_site_failure_after_a_joined_solve_does_not_solve_again(self):
        """A joined solve's credentials that hit a site failure (not a
        rejection) are kept; a re-solve would hit the same failure."""
        handler = CountingHandler()
        handler._try_cached_request = AsyncMock(return_value=None)

        results = await asyncio.gather(*(handler.get(URL, {}) for _ in range(5)))

        assert results == [None] * 5
        assert handler.solves == 1
        assert handler.is_cache_valid()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rejected_cache_solves_and_replays(self):
        handler = CountingHandler()
        handler.cache_credentials(clearance("old"), {"User-Agent": "UA"})
        handler._try_cached_request = reject(handler, "old")

        assert await handler.get(URL, {}) == "<html>ok</html>"
        assert handler.solves == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_own_solve_rejected_returns_none_without_solving_again(self):
        """A solve this request started was rejected for it: a second solve
        right away is unlikely to do better, so leave retrying to the caller."""
        handler = CountingHandler()
        handler._try_cached_request = reject(handler, "v1")

        assert await handler.get(URL, {}) is None
        assert handler.solves == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_rejected_together_share_one_re_solve(self):
        """Callers that awaited one solve and all saw its credentials
        rejected re-solve once between them, not once each."""
        handler = CountingHandler()
        handler._try_cached_request = reject(handler, "v1")

        results = await asyncio.gather(*(handler.get(URL, {}) for _ in range(5)))

        # The caller that started the rejected solve gives up; the others
        # share one re-solve.
        assert results.count("<html>ok</html>") == 4
        assert handler.solves == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_callers_rejected_by_every_solve_stop_after_two_solves(self):
        """Callers that keep joining each other's rejected solves stop after
        their second, rather than driving a third solve in a row."""
        handler = CountingHandler()
        handler._try_cached_request = reject(handler, "v1", "v2", "v3", "v4")

        results = await asyncio.gather(*(handler.get(URL, {}) for _ in range(5)))

        assert results == [None] * 5
        assert handler.solves == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_newer_credentials_cached_during_a_rejected_replay_are_used(self):
        """Credentials another caller cached while this replay was rejected
        are replayed, not treated as already tried and solved over."""
        handler = CountingHandler()
        handler.cache_credentials(clearance("old"), {"User-Agent": "UA"})

        async def replay(_url, _headers):
            if handler._cached_cookies == "cf_clearance=old":
                # Another caller's credentials land, then our 403 arrives; the
                # generation guard keeps the newer credentials cached.
                handler.cache_credentials(clearance("new"), {"User-Agent": "UA"})
                return None
            return "<html>new</html>"

        handler._try_cached_request = AsyncMock(side_effect=replay)

        assert await handler.get(URL, {}) == "<html>new</html>"
        assert handler.solves == 0
        assert handler._try_cached_request.await_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_credentials_cleared_before_the_replay_are_skipped(self):
        """If a joined solve's credentials are cleared (another request's 403,
        or clear_cache()) before this request replays them, it moves on rather
        than replaying with no credentials."""
        handler = CountingHandler()
        replays = []

        async def replay(_url, _headers):
            replays.append(handler._cached_cookies)
            return "<html>ok</html>"

        handler._try_cached_request = AsyncMock(side_effect=replay)

        async def clear_after_first_solve():
            while handler.solves == 0 or handler._cached_headers is None:
                await asyncio.sleep(0)
            handler.clear_cache()

        clearer = asyncio.ensure_future(clear_after_first_solve())
        waiter = asyncio.ensure_future(handler.get(URL, {}))
        starter = asyncio.ensure_future(handler.get(URL, {}))

        results = await asyncio.gather(waiter, starter, clearer)

        assert None not in replays  # never replayed without credentials
        assert all(r in ("<html>ok</html>", None) for r in results[:2])

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_makes_a_bounded_number_of_replays(self):
        """Even if every replay is rejected while newer credentials keep
        arriving, get() stops instead of looping."""
        handler = CountingHandler()
        handler.cache_credentials(clearance("c0"), {"User-Agent": "UA"})
        replays = 0

        async def always_superseded(_url, _headers):
            nonlocal replays
            replays += 1
            handler.cache_credentials(clearance(f"c{replays}"), {"User-Agent": "UA"})
            return None

        handler._try_cached_request = AsyncMock(side_effect=always_superseded)

        assert await handler.get(URL, {}) is None
        assert replays == 3
        assert handler.solves == 0


class TestSubclassing:
    @pytest.mark.unit
    def test_subclass_without_a_solve_cannot_be_constructed(self):
        class Incomplete(CachedCredentialHandler):
            pass

        with pytest.raises(TypeError, match="_solve"):
            Incomplete()
