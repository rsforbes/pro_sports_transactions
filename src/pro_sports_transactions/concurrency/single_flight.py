"""Shares one run of an async job between concurrent callers."""

import asyncio
from typing import Awaitable, Callable, Generic, Optional, Tuple, TypeVar

T = TypeVar("T")


class SingleFlight(Generic[T]):
    """Runs at most one job at a time: a caller that arrives while a job is
    running awaits that same job instead of starting another, so they all
    share its result, or its exception.

    The job is shielded from its callers: cancelling one caller does not
    cancel the job the others are awaiting. :meth:`close` stops a job that
    is still running.
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None

    @property
    def task(self) -> Optional[asyncio.Task]:
        """The job in progress, if any."""
        return self._task

    async def run(self, job: Callable[[], Awaitable[T]]) -> Tuple[Optional[T], bool]:
        """Join the job in progress, or start ``job()``.

        Returns the job's result and whether this call started it. If the job
        itself was cancelled (by :meth:`close`), the result is ``None``; a
        cancellation of this caller still propagates.
        """
        loop = asyncio.get_running_loop()
        task = self._task
        # A task from an earlier asyncio.run() belongs to a closed loop.
        started = task is None or task.done() or task.get_loop() is not loop
        if started:
            task = loop.create_task(job())

            def finished(done: asyncio.Task):
                # A callback rather than a finally in the job: a job left on
                # a closed loop is never finished, only garbage-collected, and
                # code run then has no event loop.
                if self._task is done:
                    self._task = None
                # Mark the exception retrieved, so a job whose every caller
                # was cancelled does not log "Task exception was never
                # retrieved".
                if not done.cancelled():
                    done.exception()

            # Added before any caller's callback, so it runs before they resume.
            task.add_done_callback(finished)
            self._task = task
        try:
            return await asyncio.shield(task), started
        except asyncio.CancelledError:
            if task.cancelled() and not asyncio.current_task().cancelling():
                return None, started
            raise

    async def wait(self, timeout: Optional[float] = None) -> bool:
        """Await a job still running on this event loop, without cancelling it.

        Returns ``False`` if ``timeout`` seconds passed with the job still
        running (it keeps running), else ``True``.
        """
        return await self._finish(cancel=False, timeout=timeout)

    async def close(self):
        """Cancel and await a job still running on this event loop."""
        await self._finish(cancel=True)

    async def _finish(self, cancel: bool, timeout: Optional[float] = None) -> bool:
        task = self._task
        if (
            task is not None
            and not task.done()
            and task.get_loop() is asyncio.get_running_loop()
        ):
            if cancel:
                task.cancel()
            # wait(), not await: the job's outcome is not ours to raise, but a
            # cancellation of the caller itself still propagates.
            done, _ = await asyncio.wait([task], timeout=timeout)
            return bool(done)
        return True
