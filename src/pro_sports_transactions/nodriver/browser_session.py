"""Owns the Chromium-based browser that nodriver drives."""

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from ..concurrency.loop_bound import LoopBound

if TYPE_CHECKING:  # avoid a runtime import cycle through handlers/
    from .nodriver_config import NodriverConfig

INSTALL_HINT = (
    "NodriverRequestHandler requires the 'nodriver' extra and a Chromium-based "
    "browser (Google Chrome recommended): pip install pro_sports_transactions[nodriver]"
)


class BrowserSession:
    """Launches one browser on demand, reuses it, and shuts it down.

    Any Chromium-based browser nodriver can drive (``browser_executable_path``);
    Google Chrome is the tested choice.

    The browser's CDP connection belongs to the event loop that launched it.
    Each ``asyncio.run()`` creates a new loop and closes it on exit, so a session
    reused across ``asyncio.run()`` calls would otherwise drive a dead
    connection - observed live to hang indefinitely. So a browser still running
    when its loop ends is stopped then, on that loop, even if :meth:`close` is
    never called, and :meth:`browser` on a later loop launches a new one. A
    browser left from a loop that ended without that (one not run by
    ``asyncio.run()``) is stopped when :meth:`browser` detects the loop change
    (see :class:`~pro_sports_transactions.concurrency.LoopBound`).

    Attributes:
        stop_timeout: Seconds to wait for the browser process to exit after
            stopping it, before killing it (and again after killing it).
    """

    stop_timeout: float = 10

    def __init__(self, config: "NodriverConfig"):
        self.config = config
        # Fail fast on a missing extra: raised at construction, the install hint
        # reaches the caller instead of being swallowed by a handler's
        # None-on-failure contract later.
        self.nodriver = self.import_nodriver()
        self._browsers = LoopBound(
            self._launch,
            self._stop,
            self._alive,
            name="browser",
            log_level=logging.INFO,  # a relaunch is slow; say why it happens
        )

    @staticmethod
    def import_nodriver():
        """Import the optional ``nodriver`` package, with an install hint if missing."""
        try:
            import nodriver  # noqa: PLC0415
        except ImportError as e:
            raise ImportError(INSTALL_HINT) from e
        return nodriver

    @property
    def is_running(self) -> bool:
        """True while a launched browser process is alive."""
        browser = self._browsers.resource
        return browser is not None and self._alive(browser)

    async def browser(self):
        """A live browser on the running event loop, launching one if needed."""
        return await self._browsers.get()

    async def close(self):
        """Stop the browser (if any) and free its resources."""
        await self._browsers.close()

    async def _launch(self):
        return await self.nodriver.start(
            browser_executable_path=self.config.browser_executable_path,
            headless=self.config.headless,
            sandbox=self.config.sandbox,
            browser_args=list(self.config.browser_args),
        )

    async def _stop(self, browser):
        # stop() signals the process but never waits for it (and drops it if
        # every signal fails). Unreaped, its asyncio transport is only cleaned
        # up by the garbage collector after asyncio.run() has closed the loop,
        # which prints "RuntimeError: Event loop is closed" at exit. So wait
        # for it here. A browser from an earlier, closed loop can't be waited
        # on: the wait raises, and LoopBound logs it (its close is best-effort).
        process = getattr(browser, "_process", None)
        browser.stop()
        if process is None:
            return
        try:
            await asyncio.wait_for(process.wait(), self.stop_timeout)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):  # exited meanwhile
                process.kill()
            await asyncio.wait_for(process.wait(), self.stop_timeout)

    @staticmethod
    def _alive(browser) -> bool:
        return not getattr(browser, "stopped", False)
