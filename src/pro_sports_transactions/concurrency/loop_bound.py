"""Holds a resource that belongs to the event loop that created it."""

import asyncio
import logging
from typing import Awaitable, Callable, Generic, Optional, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class LoopBound(Generic[T]):
    """Opens one resource on demand, reuses it, and closes it.

    A resource such as a browser connection or an ``aiohttp`` session belongs
    to the event loop that created it. Each ``asyncio.run()`` creates a new
    loop and closes it on exit, so a resource reused across ``asyncio.run()``
    calls would otherwise be driven on a dead loop. :meth:`get` detects the
    loop change, closes the old resource, and opens a new one. It also
    replaces a resource that died on its own, and opens one after
    :meth:`close`.

    Closing is best-effort: a resource from a loop that has since closed
    cannot always be closed cleanly.

    Attributes:
        name: What the resource is, for log messages.
        log_level: The level to log a loop-change replacement at: INFO for
            a costly one (relaunching a browser), DEBUG for a cheap one.
    """

    def __init__(
        self,
        opener: Callable[[], Awaitable[T]],
        closer: Callable[[T], Awaitable[None]],
        is_alive: Callable[[T], bool],
        name: str = "resource",
        log_level: int = logging.DEBUG,
    ):
        self._opener = opener
        self._closer = closer
        self._is_alive = is_alive
        self.name = name
        self.log_level = log_level
        self._resource: Optional[T] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def resource(self) -> Optional[T]:
        """The resource last opened, if not yet closed; never opens one."""
        return self._resource

    async def get(self) -> T:
        """A live resource on the running event loop, opening one if needed."""
        loop = asyncio.get_running_loop()
        while self._resource is not None:
            resource = self._resource
            if self._loop is not loop:
                logger.log(
                    self.log_level, "event loop changed; replacing the %s", self.name
                )
                # Dropped before awaiting, so a concurrent get() on the new
                # loop does not close it too.
                self._resource = self._loop = None
                await self._close_quietly(resource)
                # A get() or close() while awaiting may have opened or closed
                # one: look again rather than return a closed resource.
                continue
            if not self._is_alive(resource):
                self._resource = self._loop = None  # died; nothing to close
                break
            return resource
        resource = await self._opener()
        current = self._resource
        if current is not None and self._loop is loop and self._is_alive(current):
            # A concurrent get() opened one while this one awaited: share it
            # rather than overwrite (and leak) it. Look again after closing
            # ours, in case a close() ran meanwhile.
            await self._close_quietly(resource)
            return await self.get()
        self._resource, self._loop = resource, loop
        return resource

    async def close(self):
        """Close the resource (if any); a later :meth:`get` opens a new one."""
        resource, self._resource, self._loop = self._resource, None, None
        if resource is not None:
            await self._close_quietly(resource)

    async def _close_quietly(self, resource: T):
        try:
            await self._closer(resource)
        except Exception as e:
            logger.debug("%s close failed: %s", self.name, e)
