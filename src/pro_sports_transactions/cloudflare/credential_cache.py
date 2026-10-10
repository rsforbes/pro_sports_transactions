"""Holds one set of Cloudflare session credentials until they expire."""

import time
from typing import Dict, List, Optional

# The cookie that actually gates Cloudflare access; cache validity is anchored
# to its lifetime rather than to unrelated first-party or short-lived cookies.
SESSION_COOKIE = "cf_clearance"

# Credentials are refreshed this many seconds before they expire.
REFRESH_MARGIN = 300


class CredentialCache:
    """Stores the cookies and headers of one Cloudflare session and when they
    expire.

    Every :meth:`store` starts a new *generation*, so callers can tell "are
    these still the credentials I used?" even for cookie-less sessions, whose
    cookie string (``None``) is identical across stores.
    """

    def __init__(self):
        self._cookies: Optional[str] = None
        self._headers: Optional[Dict[str, str]] = None
        self._expiry: float = 0
        self._generation: int = 0

    @property
    def cookies(self) -> Optional[str]:
        """The cached cookies as a ``Cookie`` header value, or ``None``."""
        return self._cookies

    @property
    def headers(self) -> Optional[Dict[str, str]]:
        """The cached headers, or ``None`` when nothing is cached."""
        return self._headers

    @property
    def expiry(self) -> float:
        """When the cached credentials stop being used (unix time), or 0."""
        return self._expiry

    @property
    def generation(self) -> int:
        """Increases with every :meth:`store`."""
        return self._generation

    def store(self, cookies: List[dict], headers: Dict[str, str]) -> int:
        """Cache ``cookies`` and ``headers`` and return their generation.

        Args:
            cookies: Cookie dicts (``name``/``value`` required, optional
                ``expires`` unix timestamp).
            headers: Headers to send with the cookies.
        """
        # Everything that can raise on malformed input (a cookie without a
        # name, a non-numeric expires, headers that are not a mapping) runs
        # before any state changes, so a bad store cannot leave new headers
        # paired with the previous credentials' expiry.
        cookie_header = (
            "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in cookies)
            if cookies
            else None
        )
        # A copy: a caller that later changes its dict (e.g. its User-Agent)
        # must not change what is sent with cf_clearance. None is kept as None
        # (an invalid cache), as cache_credentials() has always done.
        header_copy = dict(headers) if headers is not None else None

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
                if c.get("name") == SESSION_COOKIE and (c.get("expires") or 0) > 0
            ),
            None,
        )
        if anchor is None:
            positive = [c["expires"] for c in cookies if (c.get("expires") or 0) > 0]
            anchor = min(positive) if positive else time.time() + 3600

        self._cookies = cookie_header
        self._headers = header_copy
        self._generation += 1
        # Refresh early; an already-expired anchor yields a past timestamp, so
        # is_valid() correctly reports the cache as stale.
        self._expiry = anchor - REFRESH_MARGIN
        return self._generation

    def is_valid(self) -> bool:
        """Whether credentials are cached and not yet due for refresh."""
        # Cookies are not required: a solve that cleared without a challenge
        # may yield none, and a cookie-less replay that succeeded is still a
        # valid session.
        return self._headers is not None and time.time() < self._expiry

    def holds(self, generation: int) -> bool:
        """Whether the credentials of ``generation`` are still cached (not
        cleared or replaced). Expiry is ignored."""
        return self._headers is not None and self._generation == generation

    def clear(self):
        """Clear the cached credentials."""
        self._cookies = None
        self._headers = None
        self._expiry = 0
