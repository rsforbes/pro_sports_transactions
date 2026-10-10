"""Unit tests for NodriverRequestHandler.

The browser, challenge solving, and cookie handling are tested through their
own classes under tests/unit/nodriver/, and single-flight solving and the
replay/solve decisions through CachedCredentialHandler
(test_cached_credential_handler.py). Here the handler's collaborators are
replaced so only its solve (credentials in, cache populated, failures
contained) and its use of the shared path are exercised.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from pro_sports_transactions.cloudflare import Credentials, ReplayResult
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
    handler._client = MagicMock()
    handler._client.fetch = AsyncMock(return_value=ReplayResult(text=replay))
    handler._client.close = AsyncMock()
    return handler, handler.source, handler._client.fetch


class TestNodriverRequestHandler:
    @pytest.mark.unit
    def test_assembles_collaborators(self):
        config = NodriverConfig(verify_attempts=3)
        handler = NodriverRequestHandler(config)

        assert handler.config is config
        assert isinstance(handler.session, BrowserSession)
        assert isinstance(handler.source, NodriverCredentialSource)
        assert handler.source.session is handler.session
        assert not handler.has_cached_cookies

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_caches_credentials_and_returns_replay(self):
        handler, source, replay = make_handler()

        assert await handler.get(URL, {"h": "v"}) == "<html>replayed</html>"
        source.get_credentials.assert_awaited_once_with(URL)
        replay.assert_awaited_once_with(
            URL, {"h": "v"}, {"User-Agent": "Chrome/136"}, "cf_clearance=new"
        )
        assert handler.is_cache_valid()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failed_replay_returns_none(self):
        """The browser page is never returned: if the replay with the harvested
        credentials fails, the result is None. This keeps a block page beside a
        leftover cf_clearance away from the parser."""
        handler, _, _ = make_handler(replay=None)

        assert await handler.get(URL, {}) is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_credentials_returns_none_without_caching(self):
        handler, _, replay = make_handler(credentials=None)

        assert await handler.get(URL, {}) is None
        assert not handler.has_cached_cookies
        replay.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_browser_error_returns_none_and_drops_browser(self):
        """Browser/CDP failures are contained (None-on-failure contract), and
        the browser is closed so the next call relaunches a working one."""
        handler, source, _ = make_handler()
        source.get_credentials = AsyncMock(side_effect=RuntimeError("cdp gone"))

        assert await handler.get(URL, {}) is None
        handler.session.close.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_hung_solve_times_out_returns_none_and_drops_browser(self):
        """A wedged browser must not hang get() (and every caller awaiting the
        same solve) forever."""
        handler, source, _ = make_handler()
        handler.config.solve_timeout = 0.01

        async def hang(_url):
            await asyncio.sleep(10)

        source.get_credentials = AsyncMock(side_effect=hang)

        assert await handler.get(URL, {}) is None
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
    async def test_concurrent_callers_reuse_a_cookieless_solve(self):
        """A cookie-less solve caches the same (None) cookie string every time,
        so callers awaiting it must still recognise it as new."""
        handler, source, _ = make_handler()

        async def slow_solve(_url):
            await asyncio.sleep(0.01)
            return Credentials(cookies=[], user_agent="Chrome/136")

        source.get_credentials.side_effect = slow_solve

        await asyncio.gather(*(handler.get(URL, {}) for _ in range(3)))

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
        replay.assert_awaited_once_with(
            URL, {"h": "v"}, {"User-Agent": "Chrome/136"}, "cf_clearance=tok"
        )
        source.get_credentials.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_does_not_solve_on_a_site_failure(self):
        """A failed replay of valid credentials that were not rejected must not
        launch the browser."""
        handler, source, replay = make_handler(replay=None)
        handler.cache_credentials(
            [{"name": "cf_clearance", "value": "tok", "expires": time.time() + 1000}],
            {"User-Agent": "Chrome/136"},
        )

        assert await handler.get(URL, {}) is None
        source.get_credentials.assert_not_called()
        replay.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_context_manager_closes_session(self):
        handler, _, _ = make_handler()

        async with handler as entered:
            assert entered is handler

        handler.session.close.assert_awaited_once()
        handler._client.close.assert_awaited_once()

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

        handler._client = MagicMock()
        handler._client.fetch = AsyncMock(
            return_value=ReplayResult(text="<html>replayed</html>")
        )

        async def solve():
            handler.clear_cache()  # force the browser path
            return await handler.get(URL, {})

        assert asyncio.run(solve()) == "<html>replayed</html>"
        assert asyncio.run(solve()) == "<html>replayed</html>"
        first.stop.assert_called_once()
        assert fake_nodriver.start.await_count == 2
