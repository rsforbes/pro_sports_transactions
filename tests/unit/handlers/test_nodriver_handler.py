"""Unit tests for the nodriver in-process Cloudflare handler."""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pro_sports_transactions.handlers import NodriverConfig, NodriverRequestHandler

URL = "https://www.prosportstransactions.com/basketball/Search/SearchResults.php"


def _fake_browser(
    html="<html><table><tr><td>data</td></tr></table></html>",
    title="Basketball Transactions",
    ua="Chrome/136",
    cookies=None,
):
    """Build a mock nodriver browser whose page solves on the first check."""
    page = MagicMock()
    page.get_content = AsyncMock(return_value=html)

    async def _evaluate(expr):
        return title if "title" in expr else ua if "userAgent" in expr else None

    page.evaluate = AsyncMock(side_effect=_evaluate)
    page.verify_cf = AsyncMock()

    if cookies is None:
        cookies = [
            SimpleNamespace(
                name="cf_clearance",
                value="token",
                domain=".prosportstransactions.com",
                expires=time.time() + 3600,
            )
        ]
    browser = MagicMock()
    browser.stopped = False
    browser.get = AsyncMock(return_value=page)
    browser.cookies = MagicMock()
    browser.cookies.get_all = AsyncMock(return_value=cookies)
    browser.stop = MagicMock()
    return browser, page


class TestNodriverConfig:
    @pytest.mark.unit
    def test_config_defaults(self):
        config = NodriverConfig()
        assert config.browser_executable_path is None
        assert config.headless is False
        assert config.sandbox is False
        assert config.verify_attempts == 8
        assert config.browser_args == ["--disable-dev-shm-usage"]

    @pytest.mark.unit
    def test_config_custom_values(self):
        config = NodriverConfig(
            browser_executable_path="/usr/bin/google-chrome-stable",
            headless=True,
            verify_attempts=3,
        )
        assert config.browser_executable_path == "/usr/bin/google-chrome-stable"
        assert config.headless is True
        assert config.verify_attempts == 3


class TestNodriverHandler:
    @pytest.mark.unit
    def test_handler_initialization(self):
        handler = NodriverRequestHandler()
        assert isinstance(handler.config, NodriverConfig)
        assert not handler.has_cached_cookies
        assert handler.cache_expiry_time == 0

    @pytest.mark.unit
    def test_import_nodriver_missing_raises_with_hint(self):
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "nodriver":
                raise ImportError("boom")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(ImportError, match="nodriver"):
                NodriverRequestHandler._import_nodriver()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_solves_and_caches(self):
        handler = NodriverRequestHandler(
            NodriverConfig(settle_seconds=0, poll_interval=0)
        )
        browser, page = _fake_browser()
        with (
            patch.object(
                handler, "_ensure_browser", new_callable=AsyncMock, return_value=browser
            ),
            # The solve path replays through the shared cached request so the
            # returned markup matches later cached calls; stub it out here.
            patch.object(
                handler,
                "_try_cached_request",
                new_callable=AsyncMock,
                return_value="<html>replayed</html>",
            ),
        ):
            result = await handler._refresh_cache_and_request(URL, {})

        assert result == "<html>replayed</html>"
        # Credentials harvested from the browser are cached for cheap replay.
        assert handler.has_cached_cookies
        assert handler.is_cache_valid()
        assert handler._cached_headers["User-Agent"] == "Chrome/136"
        page.verify_cf.assert_not_called()  # solved on first check

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_unsolved_returns_none_without_caching(self):
        handler = NodriverRequestHandler(
            NodriverConfig(settle_seconds=0, poll_interval=0, verify_attempts=3)
        )
        # Challenge markers never clear -> challenge never solved.
        browser, page = _fake_browser(
            html=(
                "<html><head><title>Just a moment...</title></head>"
                "<body><script>challenge-platform _cf_chl</script></body></html>"
            )
        )
        with patch.object(
            handler, "_ensure_browser", new_callable=AsyncMock, return_value=browser
        ):
            result = await handler._refresh_cache_and_request(URL, {})

        assert result is None
        assert not handler.has_cached_cookies
        assert page.verify_cf.await_count == 3  # tried each attempt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_returns_none_without_cf_clearance(self):
        """No cf_clearance means Cloudflare did not admit us (block/error page);
        return None rather than handing bogus HTML to the parser."""
        handler = NodriverRequestHandler(
            NodriverConfig(settle_seconds=0, poll_interval=0)
        )
        cookies = [
            SimpleNamespace(
                name="other",
                value="x",
                domain=".prosportstransactions.com",
                expires=time.time() + 3600,
            )
        ]
        browser, _ = _fake_browser(cookies=cookies)
        with patch.object(
            handler, "_ensure_browser", new_callable=AsyncMock, return_value=browser
        ):
            result = await handler._refresh_cache_and_request(URL, {})

        assert result is None
        assert not handler.has_cached_cookies

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_returns_none_on_browser_error(self):
        """Browser/CDP failures are contained (None-on-failure contract), not
        propagated out of get()."""
        handler = NodriverRequestHandler(
            NodriverConfig(settle_seconds=0, poll_interval=0)
        )
        with patch.object(
            handler,
            "_ensure_browser",
            new_callable=AsyncMock,
            side_effect=RuntimeError("chrome crashed"),
        ):
            result = await handler._refresh_cache_and_request(URL, {})

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_skips_cache_when_user_agent_missing(self):
        """A None user-agent must not be cached (it would crash aiohttp replay)."""
        handler = NodriverRequestHandler(
            NodriverConfig(settle_seconds=0, poll_interval=0)
        )
        browser, _ = _fake_browser(ua=None)
        with patch.object(
            handler, "_ensure_browser", new_callable=AsyncMock, return_value=browser
        ):
            result = await handler._refresh_cache_and_request(URL, {})

        assert result is not None
        assert not handler.has_cached_cookies

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_replays_cache_when_solved_under_lock(self):
        """If the cache became valid while awaiting the lock, replay it instead
        of launching a second browser solve."""
        handler = NodriverRequestHandler()
        handler.cache_credentials(
            [{"name": "cf_clearance", "value": "tok", "expires": time.time() + 1000}],
            {"User-Agent": "Chrome/136"},
        )
        ensure = AsyncMock(side_effect=AssertionError("browser must not start"))
        with (
            patch.object(handler, "_ensure_browser", ensure),
            patch.object(
                handler,
                "_try_cached_request",
                new_callable=AsyncMock,
                return_value="<html>cached</html>",
            ),
        ):
            result = await handler._refresh_cache_and_request(URL, {})

        assert result == "<html>cached</html>"
        ensure.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_harvest_cookies_filters_by_host_and_formats(self):
        handler = NodriverRequestHandler()
        cookies = [
            SimpleNamespace(
                name="cf_clearance",
                value="tok",
                domain=".prosportstransactions.com",
                expires=time.time() + 3600,
            ),
            SimpleNamespace(
                name="other",
                value="x",
                domain=".example.com",
                expires=-1,
            ),
            SimpleNamespace(
                name="session",
                value="s",
                domain="",
                expires=-1,
            ),
            SimpleNamespace(
                # Substring of the host but NOT a domain suffix: the old
                # `domain in host` test would wrongly keep this.
                name="substring",
                value="z",
                domain="sportstransactions.com",
                expires=-1,
            ),
        ]
        browser = MagicMock()
        browser.cookies = MagicMock()
        browser.cookies.get_all = AsyncMock(return_value=cookies)

        harvested = await handler._harvest_cookies(browser, URL)

        names = {c["name"] for c in harvested}
        assert "cf_clearance" in names  # matching domain kept
        assert "session" in names  # empty domain kept
        assert "other" not in names  # foreign domain dropped
        assert "substring" not in names  # substring-but-not-suffix dropped
        cf = next(c for c in harvested if c["name"] == "cf_clearance")
        assert "expires" in cf
        session = next(c for c in harvested if c["name"] == "session")
        assert "expires" not in session  # session cookie (expires <= 0) omitted

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_uses_cached_path_when_valid(self):
        handler = NodriverRequestHandler()
        handler.cache_credentials(
            [{"name": "cf_clearance", "value": "tok", "expires": time.time() + 1000}],
            {"User-Agent": "Chrome/136"},
        )
        with patch.object(
            handler,
            "_try_cached_request",
            new_callable=AsyncMock,
            return_value="<html>cached</html>",
        ) as cached:
            result = await handler.get(URL, {"h": "v"})

        assert result == "<html>cached</html>"
        cached.assert_awaited_once_with(URL, {"h": "v"})

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_stops_browser(self):
        handler = NodriverRequestHandler()
        browser, _ = _fake_browser()
        handler._browser = browser
        await handler.close()
        browser.stop.assert_called_once()
        assert handler._browser is None
