"""Session credentials harvested from a browser that cleared Cloudflare."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Credentials:
    """What a quick (plain HTTP) request needs to pass Cloudflare.

    Attributes:
        cookies: Cookies for the target host, as ``{"name", "value"}`` dicts
            with an optional ``expires`` unix timestamp (the format
            ``CachedCredentialHandler.cache_credentials`` takes). Normally
            includes ``cf_clearance``.
        user_agent: The browser's exact user-agent. ``cf_clearance`` is only
            accepted alongside the user-agent it was issued to.
    """

    cookies: List[dict]
    user_agent: str
