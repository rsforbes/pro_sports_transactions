"""Base classes for HTTP request handling."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# The cookie that actually gates Cloudflare access; cache validity is anchored
# to its lifetime rather than to unrelated first-party or short-lived cookies.
_SESSION_COOKIE = "cf_clearance"

# Bounded retry for the cached-replay hot path so a momentary network blip does
# not escalate to an expensive fresh credential refresh (a full browser solve).
_REPLAY_ATTEMPTS = 3


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
    ...), so subclasses implement just ``_refresh_cache_and_request``. The cache
    lifecycle and the fast replay path are shared here.
    """

    def __init__(self):
        self._cached_cookies: Optional[str] = None
        self._cached_headers: Optional[Dict[str, str]] = None
        self._cache_expiry: float = 0
        # Bumped on every cache_credentials() call, so "are these still the
        # credentials I used?" works even for cookie-less sessions, whose
        # cookie string (None) is identical across solves.
        self._cache_generation: int = 0

    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        # Fast path: replay cached credentials if they are still valid.
        if self.is_cache_valid():
            result = await self._try_cached_request(url, headers)
            if result is not None:
                return result

        # Cache miss, expired, or the cached credentials were rejected.
        return await self._refresh_cache_and_request(url, headers)

    @abstractmethod
    async def _refresh_cache_and_request(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Obtain fresh credentials, populate the cache via
        ``cache_credentials``, fulfil this request, and return the response
        text (or ``None`` on failure)."""

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
        403 means the credentials are stale (clear and give up); a transient
        network error is retried a few times so a blip does not trigger an
        expensive fresh refresh.
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
                        if response.status == 403:
                            # Cloudflare rejected the session - credentials stale
                            logger.warning("Session credentials rejected (403)")
                            if self._cache_generation == sent_generation:
                                self.clear_cache()
                            return None
                        # These messages say "cached-session", not "credential":
                        # Semgrep's python-logger-credential-disclosure rule flags
                        # any "credential" log message with a %s placeholder.
                        logger.warning(
                            "Cached-session request failed with status %d: %s",
                            response.status,
                            # errors="replace": a non-UTF-8 error body must not
                            # raise UnicodeDecodeError out of the log call.
                            await response.text(errors="replace"),
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
        browser, override this. Cached credentials are kept.

        Every built-in handler supports ``close()`` and ``async with``, so
        handlers can be swapped without changing the calling code. (Defined on
        the concrete handlers rather than the abstract ``RequestHandler`` so
        custom handlers' method resolution is unaffected.)
        """

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
