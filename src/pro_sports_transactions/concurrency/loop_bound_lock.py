"""An asyncio lock that follows the running event loop."""

import asyncio
from typing import Optional


class LoopBoundLock:
    """Provides an :class:`asyncio.Lock` for the currently running event loop.

    An ``asyncio.Lock`` belongs to the loop it is first contended on. Each
    ``asyncio.run()`` creates a new loop and closes it on exit, so a long-lived
    object reused across ``asyncio.run()`` calls needs a fresh lock per loop.
    """

    def __init__(self):
        self._lock: Optional[asyncio.Lock] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def get(self) -> asyncio.Lock:
        """The lock for the running loop, created on first use in that loop."""
        loop = asyncio.get_running_loop()
        if self._lock is None or loop is not self._loop:
            self._lock = asyncio.Lock()
            self._loop = loop
        return self._lock
