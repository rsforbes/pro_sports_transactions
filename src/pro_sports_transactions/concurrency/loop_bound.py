"""Holds a resource that belongs to the event loop that created it."""

import asyncio
import functools
import logging
from typing import Awaitable, Callable, Generic, Optional, TypeVar

from .single_flight import SingleFlight

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

    An open runs as its own task, shared by every :meth:`get` that needs it:
    concurrent callers get one resource, and a caller cancelled mid-open
    leaves the resource stored rather than orphaned (a browser launch
    cancelled halfway would leave its process running). :meth:`close`
    waits for an open in progress and closes what it opened; after
    :attr:`close_timeout` it stops waiting, and the open closes its resource
    whenever it finishes.

    Closing is best-effort: a resource from a loop that has since closed
    cannot always be closed cleanly.

    Attributes:
        name: What the resource is, for log messages.
        log_level: The level to log a loop-change replacement at: INFO for
            a costly one (relaunching a browser), DEBUG for a cheap one.
        close_timeout: Seconds :meth:`close` waits for an open in progress,
            so a hung open (a browser that never answers) cannot hang it.
    """

    close_timeout: float = 30

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
        self._opening: SingleFlight[Optional[T]] = SingleFlight()
        # Advanced by close(), so an open it overlapped closes its resource
        # instead of keeping it.
        self._closes = 0

    @property
    def resource(self) -> Optional[T]:
        """The resource last opened, if not yet closed; never opens one."""
        return self._resource

    async def get(self) -> T:
        """A live resource on the running event loop, opening one if needed."""
        loop = asyncio.get_running_loop()
        while True:
            resource = self._resource
            if resource is None:
                # The close count is read when the open's task is created, not
                # when it first runs: a close() scheduled in between must
                # still count as overlapping it.
                open_ = functools.partial(self._open, self._closes)
                resource, _ = await self._opening.run(open_)
                if resource is not None and resource is self._resource:
                    return resource
                # A close() overlapped the open, or took the resource before
                # this caller resumed: look again rather than return a
                # closed resource.
                continue
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
                continue
            return resource

    async def close(self):
        """Close the resource (if any); a later :meth:`get` opens a new one.

        An open in progress is awaited, and closes what it opened.
        """
        self._closes += 1
        # Awaited, not cancelled: a launch cancelled halfway can leave its
        # process running. The open's failure is not ours to raise.
        if not await self._opening.wait(self.close_timeout):
            logger.warning(
                "%s still opening after %ss; it will be closed when it opens",
                self.name,
                self.close_timeout,
            )
            # Its resource is discarded, so a later get() must not join it:
            # a launch that never answers would hang every get() after it.
            self._opening = SingleFlight()
        resource, self._resource, self._loop = self._resource, None, None
        if resource is not None:
            await self._close_quietly(resource)

    async def _open(self, closes: int) -> Optional[T]:
        if self._closes != closes:
            return None  # closed before it started: launch nothing
        resource = await self._opener()
        if self._closes != closes:
            # A close() ran meanwhile and waits for this open to close it.
            await self._close_quietly(resource)
            return None
        # Stored by the open itself, so it is kept even if every caller was
        # cancelled meanwhile.
        self._resource, self._loop = resource, asyncio.get_running_loop()
        return resource

    async def _close_quietly(self, resource: T):
        try:
            await self._closer(resource)
        except Exception as e:
            logger.debug("%s close failed: %s", self.name, e)
