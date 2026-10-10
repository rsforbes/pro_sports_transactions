"""Base classes for HTTP request handling."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..cloudflare.credential_cache import CredentialCache
from ..cloudflare.credentialed_client import CredentialedClient
from ..cloudflare.single_flight import SingleFlight

# Most requests one get() makes: the cached credentials, then up to two sets of
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
    ...), so subclasses implement just ``_solve``. The rest is built from
    pieces in :mod:`pro_sports_transactions.cloudflare` that any strategy
    shares: a :class:`CredentialCache`, a :class:`CredentialedClient` that
    sends the requests, and a :class:`SingleFlight` so that concurrent
    requests needing fresh credentials share one solve - its credentials, its
    failure, or its exception - instead of each solving in turn.
    """

    def __init__(self):
        self._cache = CredentialCache()
        self._client = CredentialedClient()
        self._solves: SingleFlight[Optional[int]] = SingleFlight()

    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        """Each round requests once, with the cached credentials or, when
        there are none, with those of a solve (joined if one is in progress).

        A success returns the page. A site failure (404, 5xx, timeout) returns
        ``None``: fresh credentials would hit it too, so retrying is left to
        the caller. A rejection clears those credentials and moves on to newer
        ones, unless they came from a solve this request started, or from its
        second solve: another solve right away is unlikely to do better.
        Bounded, so a request never loops.
        """

        async def solve() -> Optional[int]:
            # The generation the subclass's solve cached, or None. A solve that
            # reports success without caching anything counts as failed.
            before = self._cache.generation
            if (
                await self._solve(url)
                and self._cache.generation != before
                and self._cache.headers is not None
            ):
                return self._cache.generation
            return None

        solves = 0
        for _ in range(_FETCH_ROUNDS):
            # Through the public methods, not self._cache, so a subclass that
            # overrides is_cache_valid() or clear_cache() is still consulted.
            generation = self._cache.generation if self.is_cache_valid() else None
            started = False
            if generation is None:
                generation, started = await self._solves.run(solve)
                solves += 1
                if generation is None:
                    return None

            # A joined solve's credentials can be rejected for another request
            # (or cleared) before this one sends them: skip to newer ones.
            if self._cache.holds(generation):
                result = await self._client.fetch(
                    url, headers, self._cache.headers, self._cache.cookies
                )
                if result.text is not None:
                    return result.text
                if not result.rejected:
                    return None
                # Only these credentials: not newer ones another request
                # stored while this one was in flight.
                if self._cache.holds(generation):
                    self.clear_cache()
            if started or solves == 2:
                return None
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
        return self._cache.is_valid()

    def cache_credentials(self, cookies: List[dict], response_headers: dict):
        """Cache cookies and headers with expiration.

        Args:
            cookies: List of cookie dictionaries (``name``/``value`` required,
                optional ``expires`` unix timestamp)
            response_headers: Headers to send on cached replay requests

        Useful for manually managing cache or pre-warming credentials.
        """
        self._cache.store(cookies, response_headers)

    def clear_cache(self):
        """Clear cached credentials and force fresh requests.

        Useful for forcing fresh authentication or freeing memory.
        """
        self._cache.clear()

    @property
    def has_cached_cookies(self) -> bool:
        """Check if cookies are currently cached (read-only).

        Useful for debugging and monitoring cache state.
        """
        return self._cache.cookies is not None

    @property
    def cache_expiry_time(self) -> float:
        """Get the cache expiration timestamp (read-only).

        Returns:
            Unix timestamp when cache expires, or 0 if no cache

        Useful for debugging and monitoring cache lifetime.
        """
        return self._cache.expiry

    async def close(self):
        """Release resources held by the handler: stop a solve still running
        (it is shielded from its callers, so one a cancelled request left
        behind could otherwise acquire resources, such as a browser, after the
        handler is closed), then close the connections the cached-credential
        requests share. Subclasses that own resources override this and call
        it first. Cached credentials are kept, and a later request reopens
        what it needs.

        Every built-in handler supports ``close()`` and ``async with``, so
        handlers can be swapped without changing the calling code. (Defined on
        the concrete handlers rather than the abstract ``RequestHandler`` so
        custom handlers' method resolution is unaffected.)
        """
        await self._solves.close()
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
