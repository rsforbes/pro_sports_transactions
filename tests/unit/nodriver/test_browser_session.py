"""Unit tests for BrowserSession."""

import asyncio
import sys
from unittest.mock import AsyncMock, patch

import pytest

from pro_sports_transactions.nodriver import BrowserSession, NodriverConfig


class TestBrowserSession:
    @pytest.mark.unit
    def test_missing_extra_raises_with_hint(self):
        """A missing extra must fail at construction with the install hint."""
        # A None entry in sys.modules makes `import nodriver` raise ImportError.
        with patch.dict(sys.modules, {"nodriver": None}):
            with pytest.raises(
                ImportError, match=r"pro_sports_transactions\[nodriver\]"
            ):
                BrowserSession(NodriverConfig())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_launches_with_config(self, fake_nodriver, make_fake_browser):
        browser, _ = make_fake_browser()
        fake_nodriver.start = AsyncMock(return_value=browser)
        config = NodriverConfig(browser_executable_path="/usr/bin/google-chrome")
        session = BrowserSession(config)

        assert await session.browser() is browser
        assert session.is_running
        kwargs = fake_nodriver.start.await_args.kwargs
        assert kwargs["browser_executable_path"] == "/usr/bin/google-chrome"
        assert kwargs["headless"] is False
        assert kwargs["browser_args"] == ["--disable-dev-shm-usage"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_same_loop_reuses_browser(self, fake_nodriver, make_fake_browser):
        browser, _ = make_fake_browser()
        fake_nodriver.start = AsyncMock(return_value=browser)
        session = BrowserSession(NodriverConfig())

        await session.browser()
        await session.browser()

        fake_nodriver.start.assert_awaited_once()
        browser.stop.assert_not_called()

    @pytest.mark.unit
    def test_new_event_loop_relaunches_browser(self, fake_nodriver, make_fake_browser):
        """Each asyncio.run() makes a new loop and closes it on exit. A browser
        launched on an earlier loop has a dead connection (observed live to hang
        get()), so a later loop must stop it and launch a new one."""
        first, _ = make_fake_browser()
        second, _ = make_fake_browser()
        fake_nodriver.start = AsyncMock(side_effect=[first, second])
        session = BrowserSession(NodriverConfig())

        assert asyncio.run(session.browser()) is first
        assert asyncio.run(session.browser()) is second

        first.stop.assert_called_once()  # old-loop browser shut down
        assert fake_nodriver.start.await_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exited_browser_is_replaced(self, fake_nodriver, make_fake_browser):
        first, _ = make_fake_browser()
        second, _ = make_fake_browser()
        fake_nodriver.start = AsyncMock(side_effect=[first, second])
        session = BrowserSession(NodriverConfig())

        await session.browser()
        first.stopped = True  # process exited on its own

        assert await session.browser() is second
        first.stop.assert_not_called()  # nothing left to stop

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_stops_browser(self, fake_nodriver, make_fake_browser):
        browser, _ = make_fake_browser()
        fake_nodriver.start = AsyncMock(return_value=browser)
        session = BrowserSession(NodriverConfig())
        await session.browser()

        await session.close()

        browser.stop.assert_called_once()
        assert not session.is_running
