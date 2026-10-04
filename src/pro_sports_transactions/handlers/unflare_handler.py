"""Unflare proxy request handler for bypassing Cloudflare protection."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiohttp

from .base_handler import CachedCredentialHandler, RequestConfig

logger = logging.getLogger(__name__)


@dataclass
class UnflareConfig(RequestConfig):
    """Configuration for Unflare proxy requests"""

    url: str = "http://localhost:5002/scrape"
    timeout: int = 60000
    proxy: Optional[Dict[str, any]] = None


class UnflareRequestHandler(CachedCredentialHandler):
    """Unflare proxy request handler for bypassing Cloudflare.

    Fetches fresh ``cf_clearance`` credentials from an Unflare service, then
    relies on :class:`CachedCredentialHandler` to cache and replay them.
    """

    def __init__(self, config: Optional[UnflareConfig] = None):
        super().__init__()
        self.config = config or UnflareConfig()

    def cache_credentials(self, cookies: List[dict], unflare_headers: dict):
        """Cache cookies and headers with expiration.

        Args:
            cookies: List of cookie dictionaries from Unflare response
            unflare_headers: Headers dictionary from Unflare response

        Useful for manually managing cache or pre-warming credentials.
        """
        # Keeps the released keyword name (``unflare_headers``); the shared base
        # calls it ``response_headers``.
        super().cache_credentials(cookies, unflare_headers)

    async def _solve(self, url: str) -> bool:
        """Get fresh cookies from Unflare and cache them.

        Returns whether credentials were cached. The shared base runs one at a
        time and shares it, so concurrent callers with an expired cache
        trigger one Unflare solve, not one each, then replay the result.
        """
        logger.info("Requesting fresh credentials from Unflare")
        request_data = {"url": url, "timeout": self.config.timeout, "method": "GET"}

        if self.config.proxy:
            request_data["proxy"] = self.config.proxy

        timeout = aiohttp.ClientTimeout(total=120)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.config.url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status != 200:
                        logger.warning(
                            "Unflare service returned status %d: %s",
                            response.status,
                            await response.text(),
                        )
                        return False

                    result = await response.json()
                    if not isinstance(result, dict):
                        logger.error(
                            "Unflare returned an unexpected payload type: %s",
                            type(result).__name__,
                        )
                        return False

                    if result.get("code") == "error":
                        logger.error(
                            "Unflare error: %s",
                            result.get("message", "Unknown error"),
                        )
                        return False

                    # "or": a JSON null must not be cached - None headers mean
                    # "no cache" and would break the replay's header merge.
                    cookies = result.get("cookies") or []
                    unflare_headers = result.get("headers") or {}
                    if not (
                        isinstance(cookies, list)
                        and all(
                            isinstance(c, dict)
                            and "name" in c
                            and "value" in c
                            # cache_credentials() compares expires to 0
                            and isinstance(c.get("expires") or 0, (int, float))
                            for c in cookies
                        )
                        and isinstance(unflare_headers, dict)
                        and all(isinstance(v, str) for v in unflare_headers.values())
                    ):
                        # cache_credentials() would raise out of get() (or
                        # cache headers the replay cannot merge).
                        logger.error("Unflare returned malformed cookies or headers")
                        return False
        except (aiohttp.ClientError, OSError, ValueError) as e:
            # ValueError: a malformed JSON body (json.JSONDecodeError) must not
            # escape get() either.
            logger.error("Unflare request failed: %s", e)
            return False

        # Cached after the Unflare session closes, so its connection is not
        # held open across the base's replay and its retries.
        self.cache_credentials(cookies, unflare_headers)
        return True
