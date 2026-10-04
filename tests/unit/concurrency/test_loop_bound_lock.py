"""Unit tests for LoopBoundLock."""

import asyncio

import pytest

from pro_sports_transactions.concurrency import LoopBoundLock


class TestLoopBoundLock:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_same_loop_returns_same_lock(self):
        lock = LoopBoundLock()
        assert lock.get() is lock.get()

    @pytest.mark.unit
    def test_new_loop_gets_new_lock(self):
        lock = LoopBoundLock()

        async def grab():
            return lock.get()

        first = asyncio.run(grab())
        second = asyncio.run(grab())
        assert first is not second
