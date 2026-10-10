"""Owns the Chromium-based browser that nodriver drives."""

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
    connection - observed live to hang indefinitely. :meth:`browser` detects the
    loop change, stops the old browser, and launches a new one (see
    :class:`~pro_sports_transactions.concurrency.LoopBound`).
    """

    def __init__(self, config: "NodriverConfig"):
        self.config = config
        # Fail fast on a missing extra: raised at construction, the install hint
        # reaches the caller instead of being swallowed by a handler's
        # None-on-failure contract later.
        self.nodriver = self.import_nodriver()
        self._browser = LoopBound(
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
        browser = self._browser.resource
        return browser is not None and self._alive(browser)

    async def browser(self):
        """A live browser on the running event loop, launching one if needed."""
        return await self._browser.get()

    async def close(self):
        """Stop the browser (if any) and free its resources."""
        await self._browser.close()

    async def _launch(self):
        return await self.nodriver.start(
            browser_executable_path=self.config.browser_executable_path,
            headless=self.config.headless,
            sandbox=self.config.sandbox,
            browser_args=list(self.config.browser_args),
        )

    @staticmethod
    async def _stop(browser):
        browser.stop()

    @staticmethod
    def _alive(browser) -> bool:
        return not getattr(browser, "stopped", False)
