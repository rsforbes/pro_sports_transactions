"""Unit tests for SingleFlight."""

import asyncio
import gc

import pytest

from pro_sports_transactions.concurrency.single_flight import SingleFlight


class Job:
    """A job that counts its runs and returns the run number after a short
    wait, long enough for concurrent callers to join it."""

    def __init__(self, result=None, error=None):
        self.runs = 0
        self.result = result
        self.error = error

    async def __call__(self):
        self.runs += 1
        await asyncio.sleep(0.01)
        if self.error:
            raise self.error
        return self.result if self.result is not None else self.runs


async def run_many(flight, job, n=5):
    return await asyncio.gather(
        *(flight.run(job) for _ in range(n)), return_exceptions=True
    )


class TestSingleFlight:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_callers_share_one_run(self):
        flight, job = SingleFlight(), Job()

        results = await run_many(flight, job)

        assert job.runs == 1
        assert [value for value, _ in results] == [1] * 5
        assert [started for _, started in results] == [True] + [False] * 4

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrent_callers_share_an_exception(self):
        flight, job = SingleFlight(), Job(error=RuntimeError("boom"))

        results = await run_many(flight, job)

        assert job.runs == 1
        assert all(isinstance(r, RuntimeError) for r in results)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_a_call_after_the_job_finished_starts_a_new_run(self):
        flight, job = SingleFlight(), Job()

        assert await flight.run(job) == (1, True)
        assert await flight.run(job) == (2, True)
        assert flight.task is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancelling_one_caller_does_not_cancel_the_job(self):
        flight, job = SingleFlight(), Job()

        first = asyncio.ensure_future(flight.run(job))
        second = asyncio.ensure_future(flight.run(job))
        await asyncio.sleep(0)  # both are now awaiting the one run
        first.cancel()

        assert await second == (1, False)
        assert first.cancelled()
        assert job.runs == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_cancels_the_job_and_callers_get_none(self):
        """The job is shielded from its callers, so close() must stop one that
        a cancelled caller left behind; callers still awaiting it get None."""
        flight, job = SingleFlight(), Job()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(flight.run(job), 0.001)
        waiter = asyncio.ensure_future(flight.run(job))
        await asyncio.sleep(0)  # joined the leftover run
        task = flight.task

        await flight.close()

        assert task.cancelled()
        assert await waiter == (None, False)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_without_a_job_does_nothing(self):
        await SingleFlight().close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wait_lets_the_job_finish(self):
        flight, job = SingleFlight(), Job()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(flight.run(job), 0.001)
        task = flight.task

        await flight.wait()

        assert task.done() and not task.cancelled()
        assert task.result() == 1
        await flight.wait()  # nothing running: returns at once

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wait_gives_up_after_its_timeout(self):
        flight, release = SingleFlight(), asyncio.Event()
        running = asyncio.ensure_future(flight.run(release.wait))
        await asyncio.sleep(0)  # the job has started

        assert await flight.wait(timeout=0.01) is False
        assert not flight.task.done()  # left running, not cancelled
        release.set()
        assert await flight.wait() is True
        await running

    @pytest.mark.unit
    def test_a_new_event_loop_does_not_join_a_job_from_a_closed_one(self):
        """One SingleFlight across event loops: a job left on an earlier
        (closed) loop must not be awaited by the next."""
        flight, job = SingleFlight(), Job()

        async def interrupted():
            asyncio.ensure_future(flight.run(job))
            await asyncio.sleep(0)  # the job has started

        # Close the loop with the job still pending (asyncio.run() would
        # cancel it, which clears it and skips the loop check).
        old_loop = asyncio.new_event_loop()
        old_loop.run_until_complete(interrupted())
        old_loop.close()
        stale = flight.task
        assert stale is not None and not stale.done()

        assert asyncio.run(flight.run(job)) == (2, True)

        # The stale job is never finished, only garbage-collected: that must
        # not run code needing an event loop ("Exception ignored in ...").
        del stale
        gc.collect()
