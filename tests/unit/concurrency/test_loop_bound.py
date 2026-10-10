"""Unit tests for LoopBound."""

import asyncio
import logging

import pytest

from pro_sports_transactions.concurrency.loop_bound import LoopBound


class Resource:
    def __init__(self, number):
        self.number = number
        self.closed = False


class Factory:
    """Opens numbered resources and records which ones it closed. A close
    can be held open (``hold_close``) to let other calls run meanwhile."""

    def __init__(self, close_error=None):
        self.opened = []
        self.closed = []
        self.close_error = close_error
        self.hold_close = None

    async def open(self):
        resource = Resource(len(self.opened) + 1)
        self.opened.append(resource)
        return resource

    async def close(self, resource):
        self.closed.append(resource.number)
        if self.hold_close is not None:
            await self.hold_close.wait()
        if self.close_error:
            raise self.close_error
        resource.closed = True

    def bound(self):
        return LoopBound(self.open, self.close, lambda r: not r.closed)

    def slow_bound(self, opening):
        """A LoopBound whose opener waits for ``opening`` to be set."""

        async def slow_open():
            await opening.wait()
            return await self.open()

        return LoopBound(slow_open, self.close, lambda r: not r.closed)


class TestLoopBound:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_same_loop_reuses_the_resource(self):
        factory = Factory()
        bound = factory.bound()

        assert bound.resource is None
        first = await bound.get()

        assert await bound.get() is first
        assert bound.resource is first
        assert len(factory.opened) == 1
        assert factory.closed == []

    @pytest.mark.unit
    def test_new_event_loop_closes_and_replaces_the_resource(self, caplog):
        """Each asyncio.run() makes a new loop and closes it on exit, so a
        resource from an earlier loop is closed and a new one opened."""
        factory = Factory()
        bound = factory.bound()

        first = asyncio.run(bound.get())
        with caplog.at_level(logging.DEBUG):
            second = asyncio.run(bound.get())

        assert second is not first
        assert factory.closed == [1]
        assert [
            r.levelno
            for r in caplog.records
            if "event loop changed; replacing the resource" in r.getMessage()
        ] == [logging.DEBUG]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_dead_resource_is_replaced_without_closing(self):
        factory = Factory()
        bound = factory.bound()
        first = await bound.get()
        first.closed = True  # died on its own

        assert (await bound.get()).number == 2
        assert factory.closed == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_closes_and_a_later_get_reopens(self):
        factory = Factory()
        bound = factory.bound()
        await bound.get()

        await bound.close()
        await bound.close()  # safe to repeat

        assert bound.resource is None
        assert factory.closed == [1]
        assert (await bound.get()).number == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_failure_is_logged_not_raised(self, caplog):
        """A resource from a closed loop cannot always be closed cleanly."""
        factory = Factory(close_error=RuntimeError("loop is closed"))
        bound = factory.bound()
        await bound.get()

        with caplog.at_level(logging.DEBUG):
            await bound.close()

        assert bound.resource is None
        assert "resource close failed: loop is closed" in caplog.text

    @pytest.mark.unit
    def test_close_during_a_loop_change_still_returns_a_live_resource(self):
        """A close() while the old loop's resource is being closed must not
        leave get() returning a closed resource."""
        factory = Factory()
        bound = factory.bound()
        asyncio.run(bound.get())

        async def close_during_swap():
            factory.hold_close = asyncio.Event()
            getting = asyncio.create_task(bound.get())
            await asyncio.sleep(0)  # get() is now closing the old resource
            await bound.close()
            factory.hold_close.set()
            return await getting

        resource = asyncio.run(close_during_swap())

        assert not resource.closed
        assert bound.resource is resource

    @pytest.mark.unit
    def test_concurrent_gets_during_a_loop_change_share_one_resource(self):
        factory = Factory()
        bound = factory.bound()
        asyncio.run(bound.get())

        async def get_twice_during_swap():
            factory.hold_close = asyncio.Event()
            first = asyncio.create_task(bound.get())
            await asyncio.sleep(0)  # first get() is closing the old resource
            second = await bound.get()
            factory.hold_close.set()
            return await first, second

        first, second = asyncio.run(get_twice_during_swap())

        assert first is second
        assert len(factory.opened) == 2
        assert factory.closed == [1]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_opens_share_one_open(self):
        """Two get() calls on a fresh LoopBound open one resource between
        them, not one each."""
        factory, opening = Factory(), asyncio.Event()
        bound = factory.slow_bound(opening)
        first = asyncio.create_task(bound.get())
        second = asyncio.create_task(bound.get())
        await asyncio.sleep(0)  # both are now waiting on the open
        opening.set()

        a, b = await asyncio.gather(first, second)

        assert a is b
        assert bound.resource is a
        assert len(factory.opened) == 1
        assert factory.closed == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_caller_cancelled_mid_open_leaves_the_resource_held(self):
        """A browser launch cancelled halfway would leave its process
        running: the open finishes and its resource is kept for close()."""
        factory, opening = Factory(), asyncio.Event()
        bound = factory.slow_bound(opening)
        getting = asyncio.create_task(bound.get())
        await asyncio.sleep(0)  # now waiting on the open
        getting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await getting
        opening.set()
        await asyncio.sleep(0)  # the open finishes on its own

        assert len(factory.opened) == 1
        assert bound.resource is factory.opened[0]
        await bound.close()
        assert factory.closed == [1]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_mid_open_closes_what_it_opens(self):
        """A close() during an open waits for it and closes its resource,
        which would otherwise outlive the close()."""
        factory, opening = Factory(), asyncio.Event()
        bound = factory.slow_bound(opening)
        getting = asyncio.create_task(bound.get())
        await asyncio.sleep(0)  # now waiting on the open
        closing = asyncio.create_task(bound.close())
        await asyncio.sleep(0)  # close() is now waiting on the open
        opening.set()
        await closing
        assert factory.closed == [1]

        # The get() that overlapped the close() opens a new one rather than
        # return the closed one.
        resource = await getting
        assert resource.number == 2 and not resource.closed
        assert bound.resource is resource

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_before_the_open_starts_still_overlaps_it(self):
        """A close() that runs after get() schedules the open but before the
        open's first step must not let get() return what close() closes."""
        factory = Factory()
        bound = factory.bound()

        resource, _ = await asyncio.gather(bound.get(), bound.close())

        assert not resource.closed
        assert bound.resource is resource
        assert len(factory.opened) == 1  # the overlapped open launched nothing

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_get_after_close_mid_open_opens_a_new_one(self):
        factory, opening = Factory(), asyncio.Event()
        bound = factory.slow_bound(opening)
        getting = asyncio.create_task(bound.get())
        await asyncio.sleep(0)  # now waiting on the open
        getting.cancel()
        closing = asyncio.create_task(bound.close())
        await asyncio.sleep(0)  # close() is now waiting on the open
        opening.set()
        await closing

        assert factory.closed == [1]
        assert bound.resource is None
        assert (await bound.get()).number == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_stops_waiting_for_a_hung_open(self, caplog):
        """A launch that never answers must not hang close(); the open still
        closes its resource if it finishes later."""
        factory, opening = Factory(), asyncio.Event()
        bound = factory.slow_bound(opening)
        bound.close_timeout = 0.01
        getting = asyncio.create_task(bound.get())
        await asyncio.sleep(0)  # now waiting on the open
        await asyncio.sleep(0)  # the open is now in the opener
        getting.cancel()

        with caplog.at_level(logging.WARNING):
            await bound.close()

        assert factory.opened == []  # still opening
        assert "resource still opening after 0.01s" in caplog.text
        opening.set()
        await asyncio.sleep(0)  # the open finishes and closes its resource
        assert factory.closed == [1]
        assert bound.resource is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_get_after_close_gives_up_on_a_hung_open_opens_anew(self):
        """A get() after close() stopped waiting must not join the hung open,
        whose resource is discarded anyway: it would hang with it."""
        factory, opening = Factory(), asyncio.Event()
        launches = []

        async def first_launch_hangs():
            launches.append(None)
            if len(launches) == 1:
                await opening.wait()
            return await factory.open()

        bound = LoopBound(first_launch_hangs, factory.close, lambda r: not r.closed)
        bound.close_timeout = 0.01
        getting = asyncio.create_task(bound.get())
        await asyncio.sleep(0)  # now waiting on the open
        await asyncio.sleep(0)  # the open is now in the opener
        getting.cancel()
        await bound.close()

        resource = await asyncio.wait_for(bound.get(), 1)

        assert len(launches) == 2 and not resource.closed
        opening.set()
        await asyncio.sleep(0)  # the hung open finishes and closes its own
        assert factory.closed == [2]
        assert bound.resource is resource

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_an_open_failure_reaches_every_caller(self):
        factory = Factory()

        async def failing_open():
            await asyncio.sleep(0)
            raise RuntimeError("no browser")

        bound = LoopBound(failing_open, factory.close, lambda r: not r.closed)
        results = await asyncio.gather(bound.get(), bound.get(), return_exceptions=True)

        assert [str(r) for r in results] == ["no browser", "no browser"]
        assert bound.resource is None
        await bound.close()  # nothing to close
