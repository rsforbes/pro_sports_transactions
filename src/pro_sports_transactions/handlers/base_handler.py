"""Base classes for HTTP request handling."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import aiohttp

from ..cloudflare.challenge import challenge_present

logger = logging.getLogger(__name__)

# The cookie that actually gates Cloudflare access; cache validity is anchored
# to its lifetime rather than to unrelated first-party or short-lived cookies.
_SESSION_COOKIE = "cf_clearance"

# Bounded retry for the cached-replay hot path so a momentary network blip does
# not escalate to an expensive fresh credential refresh (a full browser solve).
_REPLAY_ATTEMPTS = 3

# Most replays one get() makes: the cached credentials, then up to two sets of
# fresh ones (see CachedCredentialHandler.get).
_FETCH_ROUNDS = 3


@dataclass
class RequestConfig:
    """Base configuration for request handling"""


class RequestHandler(ABC):
    """Abstract base class for handling HTTP requests"""

    @abstractmethod
    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        """Make a GET request and return the response text"""


class CachedCredentialHandler(RequestHandler):
    """A request handler that solves a Cloudflare challenge once, caches the
    resulting session credentials (cookies + headers), and replays cheap
    ``aiohttp`` requests until they expire.

    The expensive "how do I obtain fresh credentials" step is the only part
    that differs between strategies (an Unflare sidecar, an in-process browser,
    ...), so subclasses implement just ``_solve``. The cache lifecycle, the
    replay path, and single-flight solving are shared here.

    Single flight: at most one solve runs at a time, and every request that
    needs fresh credentials while it runs awaits that same solve, so they all
    share its outcome - its credentials, its failure, or its exception -
    instead of each solving in turn.
    """

    def __init__(self):
        self._cached_cookies: Optional[str] = None
        self._cached_headers: Optional[Dict[str, str]] = None
        self._cache_expiry: float = 0
        # Bumped on every cache_credentials() call, so "are these still the
        # credentials I used?" works even for cookie-less sessions, whose
        # cookie string (None) is identical across solves.
        self._cache_generation: int = 0
        # The solve in progress, if any; see _shared_solve().
        self._solve_task: Optional[asyncio.Task] = None

    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        """Replay ``url`` with the cached credentials, solving (or joining the
        solve in progress) when there are none.

        Each round replays once. A success returns the page. A failure that
        left the credentials cached was the site (404, 5xx, timeout), not
        Cloudflare: fresh credentials would hit it too, so return ``None`` and
        leave retrying to the caller. A rejection moves on to newer
        credentials, unless they came from a solve this request started, or
        from its second solve: another solve right away is unlikely to do
        better. (Without the second limit, callers that keep joining each
        other's rejected solves would drive a third solve in a row.) Bounded,
        so a request never loops. (Credentials a round moves on from are no
        longer cached - see ``_rejected`` - so the next round never retries
        them.)
        """
        solves = 0
        for _ in range(_FETCH_ROUNDS):
            generation = self._valid_generation()
            started = False
            if generation is None:
                generation, started = await self._shared_solve(url)
                solves += 1
                if generation is None:
                    return None

            # A joined solve's credentials can be rejected for another request
            # (or cleared) before this one replays them: skip to newer ones.
            if not self._rejected(generation):
                result = await self._try_cached_request(url, headers)
                if result is not None:
                    return result
                if not self._rejected(generation):
                    return None
            if started or solves == 2:
                return None
        return None

    def _valid_generation(self) -> Optional[int]:
        """The generation of the cached credentials, if they are valid."""
        return self._cache_generation if self.is_cache_valid() else None

    def _rejected(self, generation: int) -> bool:
        """Whether the credentials of ``generation`` are no longer cached:
        rejected by Cloudflare, cleared, or replaced by newer ones.

        A rejection clears the credentials it was sent with (see
        ``_try_cached_request``), so after a failed replay this tells a
        rejection from a site failure. Expiry is ignored: credentials that
        expired during a failed replay were not rejected.
        """
        return self._cache_generation != generation or self._cached_headers is None

    async def _shared_solve(self, url: str) -> Tuple[Optional[int], bool]:
        """Join the solve in progress, or start one.

        Returns the generation it cached (``None`` if it failed) and whether
        this call started it. A solve's exception propagates to every request
        awaiting it.
        """
        loop = asyncio.get_running_loop()
        task = self._solve_task
        # A task from an earlier asyncio.run() belongs to a closed loop.
        started = task is None or task.done() or task.get_loop() is not loop
        if started:
            task = loop.create_task(self._run_solve(url))
            # Mark the exception retrieved, so a solve whose every waiter was
            # cancelled does not log "Task exception was never retrieved".
            task.add_done_callback(lambda t: t.cancelled() or t.exception())
            self._solve_task = task
        # shield: a cancelled request must not cancel the solve that other
        # requests are awaiting.
        try:
            return await asyncio.shield(task), started
        except asyncio.CancelledError:
            # The solve itself was cancelled (close()), not this request: a
            # failed solve, so get() keeps its None-on-failure contract.
            if task.cancelled() and not asyncio.current_task().cancelling():
                return None, started
            raise

    async def _run_solve(self, url: str) -> Optional[int]:
        """Run ``_solve`` and return the generation it cached, or ``None``."""
        before = self._cache_generation
        try:
            solved = await self._solve(url)
        finally:
            if self._solve_task is asyncio.current_task():
                self._solve_task = None
        # A solve that reports success without caching anything would send
        # the replay out with no credentials; treat it as failed. Credentials
        # that are already past the early-refresh margin still count: they
        # are about to expire, not rejected.
        if (
            solved
            and self._cache_generation != before
            and self._cached_headers is not None
        ):
            return self._cache_generation
        return None

    @abstractmethod
    async def _solve(self, url: str) -> bool:
        """Obtain fresh credentials for ``url`` and store them with
        ``cache_credentials``.

        Returns whether credentials were cached. Only one runs at a time.
        Failures should be contained (logged, then ``False``) so ``get()``
        keeps its None-on-failure contract.
        """

    def is_cache_valid(self) -> bool:
        """Check if cached credentials are still valid.

        Returns:
            True if cache is valid and not expired, False otherwise
        """
        # Cookies are not required: a solve that cleared without a challenge
        # may yield none, and a cookie-less replay that succeeded is still a
        # valid session. Requiring them made every request re-solve and let
        # concurrent waiters each solve instead of reusing the fresh cache.
        return self._cached_headers is not None and time.time() < self._cache_expiry

    async def _try_cached_request(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Replay a request with the cached session credentials.

        Shared by the cached fast path and each handler's immediate post-solve
        request, so the log wording is neutral rather than cache-specific. A
        403 or a Cloudflare challenge means the credentials are stale (clear
        and give up); a transient network error is retried a few times so a
        blip does not trigger an expensive fresh refresh. Other failures leave
        the cache alone.
        """
        logger.info("Requesting with session credentials")
        # Snapshot the credentials this request uses, so a 403 only clears the
        # cache if it still holds these same (stale) credentials - not fresh ones
        # a concurrent refresh stored while this request was in flight.
        sent_generation = self._cache_generation
        sent_cookies = self._cached_cookies
        sent_headers = self._cached_headers
        fixed = {"Accept-Encoding": "gzip, deflate, br"}
        if sent_cookies:
            fixed["Cookie"] = sent_cookies
        # Merge case-insensitively, later layers winning: callers pass lowercase
        # keys (e.g. the search module's "user-agent"), and a plain dict merge
        # would keep both it and the cached "User-Agent", sending two UA headers.
        # cf_clearance is bound to the solving browser's UA, so Cloudflare then
        # rejects with 403. The same applies between the cached headers (e.g. an
        # Unflare "accept-encoding"/"cookie") and the fixed overrides.
        final_headers: Dict[str, str] = {}
        for layer in (headers, sent_headers, fixed):
            layer_keys = {k.lower() for k in layer}
            final_headers = {
                k: v for k, v in final_headers.items() if k.lower() not in layer_keys
            }
            final_headers.update(layer)

        timeout = aiohttp.ClientTimeout(total=120)
        for attempt in range(_REPLAY_ATTEMPTS):
            try:
                async with aiohttp.ClientSession(
                    headers=final_headers, timeout=timeout
                ) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.text(encoding="utf-8")
                        # errors="replace": a non-UTF-8 error body must not
                        # raise UnicodeDecodeError out of the check or the log.
                        body = await response.text(errors="replace")
                        # Cloudflare marks challenges with cf-mitigated whatever
                        # the status (e.g. a 503 "under attack" interstitial);
                        # the body marker catches a challenge served without
                        # it, which would otherwise never trigger a re-solve.
                        challenged = response.headers.get(
                            "cf-mitigated", ""
                        ).lower() == "challenge" or challenge_present(body)
                        if response.status == 403 or challenged:
                            # Cloudflare rejected the session - credentials stale
                            logger.warning(
                                "Session credentials rejected (%d)", response.status
                            )
                            if self._cache_generation == sent_generation:
                                self.clear_cache()
                            return None
                        # These messages say "cached-session", not "credential":
                        # Semgrep's python-logger-credential-disclosure rule flags
                        # any "credential" log message with a %s placeholder.
                        logger.warning(
                            "Cached-session request failed with status %d: %s",
                            response.status,
                            body,
                        )
                        return None
            except asyncio.TimeoutError as e:
                # The full 120s budget is already spent; retrying would stall
                # the caller for minutes before the refresh path even starts.
                logger.error("Cached-session request timed out: %s", e)
                return None
            except (aiohttp.ClientError, OSError) as e:
                # Transient: retry before escalating to a full refresh.
                if attempt + 1 < _REPLAY_ATTEMPTS:
                    logger.warning(
                        "Cached-session request transient error "
                        "(attempt %d/%d), retrying: %s",
                        attempt + 1,
                        _REPLAY_ATTEMPTS,
                        e,
                    )
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                logger.error("Cached-session request failed after retries: %s", e)
                return None

    def cache_credentials(self, cookies: List[dict], response_headers: dict):
        """Cache cookies and headers with expiration.

        Args:
            cookies: List of cookie dictionaries (``name``/``value`` required,
                optional ``expires`` unix timestamp)
            response_headers: Headers to send on cached replay requests

        Useful for manually managing cache or pre-warming credentials.
        """
        # Build cookie header
        self._cached_cookies = (
            "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
            if cookies
            else None
        )

        self._cached_headers = response_headers
        self._cache_generation += 1

        # Anchor validity on cf_clearance specifically - it is the cookie that
        # gates access. Keying off it (rather than the min or max over all
        # cookies) means a short-lived companion like __cf_bm cannot cap the
        # cache, and an unrelated long-lived first-party cookie cannot extend it
        # past cf_clearance's real lifetime. Fall back to the earliest positive
        # expiry, then a 1-hour default, when cf_clearance carries no expiry.
        anchor = next(
            (
                c["expires"]
                for c in cookies
                if c.get("name") == _SESSION_COOKIE and (c.get("expires") or 0) > 0
            ),
            None,
        )
        if anchor is None:
            positive = [c["expires"] for c in cookies if (c.get("expires") or 0) > 0]
            anchor = min(positive) if positive else time.time() + 3600

        # Refresh 5 minutes early; an already-expired anchor yields a past
        # timestamp, so is_cache_valid() correctly reports the cache as stale.
        self._cache_expiry = anchor - 300

    def clear_cache(self):
        """Clear cached credentials and force fresh requests.

        Useful for forcing fresh authentication or freeing memory.
        """
        self._cached_cookies = None
        self._cached_headers = None
        self._cache_expiry = 0

    @property
    def has_cached_cookies(self) -> bool:
        """Check if cookies are currently cached (read-only).

        Useful for debugging and monitoring cache state.
        """
        return self._cached_cookies is not None

    @property
    def cache_expiry_time(self) -> float:
        """Get the cache expiration timestamp (read-only).

        Returns:
            Unix timestamp when cache expires, or 0 if no cache

        Useful for debugging and monitoring cache lifetime.
        """
        return self._cache_expiry

    async def close(self):
        """Release resources held by the handler. The base holds none (each request opens
        and closes its own session); subclasses that own resources, such as a
        browser, override this and call it first. Cached credentials are kept.

        A solve still running (one a cancelled request left behind: the solve
        is shielded from its callers) is cancelled and awaited, so it cannot
        acquire resources, such as a browser, after the handler is closed.

        Every built-in handler supports ``close()`` and ``async with``, so
        handlers can be swapped without changing the calling code. (Defined on
        the concrete handlers rather than the abstract ``RequestHandler`` so
        custom handlers' method resolution is unaffected.)
        """
        task = self._solve_task
        if (
            task is not None
            and not task.done()
            and task.get_loop() is asyncio.get_running_loop()
        ):
            task.cancel()
            # wait(), not await: the solve's outcome is not ours to raise, but
            # a cancellation of close() itself still propagates.
            await asyncio.wait([task])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
