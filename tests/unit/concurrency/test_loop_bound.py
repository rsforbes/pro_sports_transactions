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
    async def test_concurrent_opens_share_one_resource(self):
        """Two get() calls that both open (the opener yields) must not leave
        one resource overwritten and never closed."""
        factory = Factory()
        opening = asyncio.Event()

        async def slow_open():
            await opening.wait()
            return await factory.open()

        bound = LoopBound(slow_open, factory.close, lambda r: not r.closed)
        first = asyncio.create_task(bound.get())
        second = asyncio.create_task(bound.get())
        await asyncio.sleep(0)  # both are now waiting in the opener
        opening.set()

        a, b = await asyncio.gather(first, second)

        assert a is b
        assert bound.resource is a
        assert len(factory.opened) == 2
        assert factory.closed == [2]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_while_dropping_a_duplicate_still_returns_a_live_one(self):
        """A close() while get() closes its duplicate must not leave get()
        returning the shared resource that close() just closed."""
        factory = Factory()
        opening = asyncio.Event()

        async def slow_open():
            await opening.wait()
            return await factory.open()

        bound = LoopBound(slow_open, factory.close, lambda r: not r.closed)
        first = asyncio.create_task(bound.get())
        second = asyncio.create_task(bound.get())
        await asyncio.sleep(0)  # both are now waiting in the opener
        factory.hold_close = asyncio.Event()
        opening.set()
        await asyncio.sleep(0)  # second is now closing its duplicate
        closing = asyncio.create_task(bound.close())
        await asyncio.sleep(0)
        factory.hold_close.set()

        _, b = await asyncio.gather(first, second)
        await closing

        assert not b.closed
        assert bound.resource is b
