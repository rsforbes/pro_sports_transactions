"""Unit tests for BrowserSession."""

import asyncio
import logging
import sys
from unittest.mock import AsyncMock, MagicMock, patch

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
    def test_new_event_loop_relaunches_browser(
        self, fake_nodriver, make_fake_browser, caplog
    ):
        """Each asyncio.run() makes a new loop and closes it on exit. A browser
        launched on an earlier loop has a dead connection (observed live to hang
        get()), so it is stopped as its loop ends and a later loop launches a
        new one."""
        first, _ = make_fake_browser()
        second, _ = make_fake_browser()
        fake_nodriver.start = AsyncMock(side_effect=[first, second])
        session = BrowserSession(NodriverConfig())

        assert asyncio.run(session.browser()) is first
        first.stop.assert_called_once()  # stopped as its loop ended
        with caplog.at_level(logging.INFO):
            assert asyncio.run(session.browser()) is second

        assert fake_nodriver.start.await_count == 2
        # A relaunch is slow, so why it happens is logged where users see it.
        assert "event loop changed; reopened the browser" in caplog.text

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

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_waits_for_process_exit(self, fake_nodriver, make_fake_browser):
        """stop() doesn't reap Chrome; an unreaped process is cleaned up after
        asyncio.run() closes the loop, printing 'Event loop is closed'."""
        browser, _ = make_fake_browser()
        process = browser._process = MagicMock()
        process.wait = AsyncMock()
        fake_nodriver.start = AsyncMock(return_value=browser)
        session = BrowserSession(NodriverConfig())
        await session.browser()

        await session.close()

        browser.stop.assert_called_once()
        process.wait.assert_awaited_once()
        process.kill.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_kills_process_that_does_not_exit(self, fake_nodriver):
        browser = MagicMock()
        process = browser._process = MagicMock()
        exited = asyncio.Event()
        process.wait = AsyncMock(side_effect=exited.wait)
        process.kill = MagicMock(side_effect=exited.set)
        session = BrowserSession(NodriverConfig())
        session.stop_timeout = 0.01

        await session._stop(browser)

        process.kill.assert_called_once()
        assert process.wait.await_count == 2  # timed out, then reaped after kill

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_bounds_wait_after_kill(self, fake_nodriver):
        """A process that survives SIGKILL (e.g. stuck in I/O) must not hang close()."""
        browser = MagicMock()
        process = browser._process = MagicMock()
        process.wait = AsyncMock(side_effect=asyncio.Event().wait)  # never exits
        session = BrowserSession(NodriverConfig())
        session.stop_timeout = 0.01

        with pytest.raises(TimeoutError):
            await session._stop(browser)
        process.kill.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_tolerates_exit_before_kill(self, fake_nodriver):
        """Chrome exiting just after the wait times out makes kill() raise
        ProcessLookupError; that is a clean exit, not a failure."""
        browser = MagicMock()
        process = browser._process = MagicMock()
        process.wait = AsyncMock(side_effect=[TimeoutError, None])
        process.kill = MagicMock(side_effect=ProcessLookupError)
        session = BrowserSession(NodriverConfig())

        await session._stop(browser)

        assert process.wait.await_count == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_without_process_attribute(self, fake_nodriver):
        """stop() must still run if nodriver's private _process is missing."""
        browser = MagicMock(spec=["stop"])
        session = BrowserSession(NodriverConfig())

        await session._stop(browser)

        browser.stop.assert_called_once()

    @pytest.mark.unit
    def test_new_event_loop_relaunches_despite_unwaitable_process(
        self, fake_nodriver, make_fake_browser
    ):
        """The old browser's process belongs to the closed loop, so waiting on
        it from the new loop raises; the relaunch must still happen."""
        first, _ = make_fake_browser()
        second, _ = make_fake_browser()
        first._process = MagicMock()
        first._process.wait = AsyncMock(
            side_effect=RuntimeError("attached to a different loop")
        )
        fake_nodriver.start = AsyncMock(side_effect=[first, second])
        session = BrowserSession(NodriverConfig())

        asyncio.run(session.browser())
        assert asyncio.run(session.browser()) is second

        first.stop.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_without_process(self, fake_nodriver, make_fake_browser):
        browser, _ = make_fake_browser()  # _process is None
        fake_nodriver.start = AsyncMock(return_value=browser)
        session = BrowserSession(NodriverConfig())
        await session.browser()

        await session.close()

        browser.stop.assert_called_once()
        assert not session.is_running
