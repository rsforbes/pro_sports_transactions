"""Owns the Chromium-based browser that nodriver drives."""

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid a runtime import cycle through handlers/
    from .nodriver_config import NodriverConfig

logger = logging.getLogger(__name__)

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
    loop change, stops the old browser, and launches a new one.
    """

    def __init__(self, config: "NodriverConfig"):
        self.config = config
        # Fail fast on a missing extra: raised at construction, the install hint
        # reaches the caller instead of being swallowed by a handler's
        # None-on-failure contract later.
        self.nodriver = self.import_nodriver()
        self._browser = None
        self._loop = None

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
        return self._browser is not None and not getattr(
            self._browser, "stopped", False
        )

    async def browser(self):
        """A live browser on the running event loop, launching one if needed."""
        loop = asyncio.get_running_loop()
        if self._browser is not None and loop is not self._loop:
            logger.info("event loop changed; relaunching the browser")
            await self.close()
        elif self._browser is not None and not self.is_running:
            self._browser = None  # process exited on its own; nothing to stop
        if self._browser is None:
            self._browser = await self.nodriver.start(
                browser_executable_path=self.config.browser_executable_path,
                headless=self.config.headless,
                sandbox=self.config.sandbox,
                browser_args=list(self.config.browser_args),
            )
            self._loop = loop
        return self._browser

    async def close(self):
        """Stop the browser (if any) and free its resources."""
        if self._browser is not None:
            try:
                self._browser.stop()
            except Exception as e:  # pragma: no cover - best-effort teardown
                logger.debug("browser stop failed: %s", e)
            self._browser = None
            self._loop = None
