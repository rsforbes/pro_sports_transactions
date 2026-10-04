"""Unit tests for NodriverRequestHandler (orchestration only).

The browser, challenge solving, and cookie handling are tested through their
own classes under tests/unit/nodriver/; here the handler's collaborators are
replaced so only its cache/solve/replay decisions are exercised.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pro_sports_transactions.cloudflare import Credentials
from pro_sports_transactions.concurrency import LoopBoundLock
from pro_sports_transactions.handlers import NodriverConfig, NodriverRequestHandler
from pro_sports_transactions.nodriver import BrowserSession, NodriverCredentialSource

URL = "https://www.prosportstransactions.com/basketball/Search/SearchResults.php"
CREDENTIALS = Credentials(
    cookies=[{"name": "cf_clearance", "value": "new", "expires": time.time() + 3600}],
    user_agent="Chrome/136",
)

pytestmark = pytest.mark.usefixtures("fake_nodriver")


def make_handler(credentials=CREDENTIALS, replay="<html>replayed</html>"):
    """A handler whose source returns ``credentials`` and whose replay returns
    ``replay``. Returns (handler, source, replay mock)."""
    handler = NodriverRequestHandler()
    handler.source = MagicMock()
    handler.source.get_credentials = AsyncMock(return_value=credentials)
    handler.session = MagicMock()
    handler.session.close = AsyncMock()
    replay_mock = AsyncMock(return_value=replay)
    handler._try_cached_request = replay_mock
    return handler, handler.source, replay_mock


class TestNodriverRequestHandler:
    @pytest.mark.unit
    def test_assembles_collaborators(self):
        config = NodriverConfig(verify_attempts=3)
        handler = NodriverRequestHandler(config)

        assert handler.config is config
        assert isinstance(handler.session, BrowserSession)
        assert isinstance(handler.source, NodriverCredentialSource)
        assert handler.source.session is handler.session
        assert isinstance(handler.solve_lock, LoopBoundLock)
        assert not handler.has_cached_cookies

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_caches_credentials_and_returns_replay(self):
        handler, source, replay = make_handler()

        result = await handler._refresh_cache_and_request(URL, {})

        assert result == "<html>replayed</html>"
        source.get_credentials.assert_awaited_once_with(URL)
        assert handler.is_cache_valid()
        assert handler._cached_cookies == "cf_clearance=new"
        assert handler._cached_headers == {"User-Agent": "Chrome/136"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failed_replay_returns_none(self):
        """The browser page is never returned: if the replay with the harvested
        credentials fails, the result is None. This keeps a block page beside a
        leftover cf_clearance away from the parser."""
        handler, _, _ = make_handler(replay=None)

        assert await handler._refresh_cache_and_request(URL, {}) is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_credentials_returns_none_without_caching(self):
        handler, _, replay = make_handler(credentials=None)

        assert await handler._refresh_cache_and_request(URL, {}) is None
        assert not handler.has_cached_cookies
        replay.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_browser_error_returns_none_and_drops_browser(self):
        """Browser/CDP failures are contained (None-on-failure contract), and
        the browser is closed so the next call relaunches a working one."""
        handler, source, _ = make_handler()
        source.get_credentials = AsyncMock(side_effect=RuntimeError("cdp gone"))

        assert await handler._refresh_cache_and_request(URL, {}) is None
        handler.session.close.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hung_solve_times_out_returns_none_and_drops_browser(self):
        """A wedged browser must not hang get() (and every caller queued on the
        solve lock) forever."""
        handler, source, _ = make_handler()
        handler.config.solve_timeout = 0.01

        async def hang(_url):
            await asyncio.sleep(10)

        source.get_credentials = AsyncMock(side_effect=hang)

        assert await handler._refresh_cache_and_request(URL, {}) is None
        handler.session.close.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cookieless_credentials_are_cached(self):
        """A solve that cleared without issuing cookies still yields a reusable
        session; it must not force a fresh browser solve on every request."""
        handler, source, _ = make_handler(
            credentials=Credentials(cookies=[], user_agent="Chrome/136")
        )

        await handler.get(URL, {})
        await handler.get(URL, {})

        assert handler.is_cache_valid()
        source.get_credentials.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_replays_cache_solved_while_waiting_for_lock(self):
        """If another caller cached credentials while we waited for the lock,
        replay them instead of launching a second browser solve."""
        handler, source, _ = make_handler(replay="<html>cached</html>")

        class SolvedWhileWaiting:
            async def __aenter__(self):
                handler.cache_credentials(
                    [{"name": "cf_clearance", "value": "tok"}],
                    {"User-Agent": "Chrome/136"},
                )

            async def __aexit__(self, *exc):
                return False

        handler.solve_lock = MagicMock()
        handler.solve_lock.get = MagicMock(return_value=SolvedWhileWaiting())

        assert (
            await handler._refresh_cache_and_request(URL, {}) == "<html>cached</html>"
        )
        source.get_credentials.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_does_not_re_replay_credentials_get_already_tried(self):
        """Credentials valid on entry were just replayed by get()'s fast path and
        failed; they must not be replayed again under the lock before solving."""
        handler, source, replay = make_handler()
        handler.cache_credentials(
            [{"name": "cf_clearance", "value": "old", "expires": time.time() + 1000}],
            {"User-Agent": "Chrome/136"},
        )

        assert await handler._refresh_cache_and_request(URL, {}) is not None
        replay.assert_awaited_once()  # only the post-solve replay
        source.get_credentials.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_uses_cached_path_when_valid(self):
        handler, source, replay = make_handler(replay="<html>cached</html>")
        handler.cache_credentials(
            [{"name": "cf_clearance", "value": "tok", "expires": time.time() + 1000}],
            {"User-Agent": "Chrome/136"},
        )

        assert await handler.get(URL, {"h": "v"}) == "<html>cached</html>"
        replay.assert_awaited_once_with(URL, {"h": "v"})
        source.get_credentials.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_context_manager_closes_session(self):
        handler, _, _ = make_handler()

        async with handler as entered:
            assert entered is handler

        handler.session.close.assert_awaited_once()

    @pytest.mark.unit
    def test_new_event_loop_relaunches_browser_end_to_end(
        self, fake_nodriver, make_fake_browser
    ):
        """One handler across two asyncio.run() calls: the second solve must
        stop the first loop's browser and launch a new one (live, reusing it
        hung get() indefinitely)."""
        first, _ = make_fake_browser()
        second, _ = make_fake_browser()
        fake_nodriver.start = AsyncMock(side_effect=[first, second])
        handler = NodriverRequestHandler(
            NodriverConfig(settle_seconds=0, poll_interval=0)
        )

        async def solve():
            handler.clear_cache()  # force the browser path
            with patch.object(
                handler,
                "_try_cached_request",
                new_callable=AsyncMock,
                return_value="<html>replayed</html>",
            ):
                return await handler._refresh_cache_and_request(URL, {})

        assert asyncio.run(solve()) == "<html>replayed</html>"
        assert asyncio.run(solve()) == "<html>replayed</html>"
        first.stop.assert_called_once()
        assert fake_nodriver.start.await_count == 2
