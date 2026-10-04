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

    async def _refresh_cache_and_request(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Get fresh cookies from Unflare and cache them"""
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
                        return None

                    result = await response.json()

                    if "code" in result and result["code"] == "error":
                        logger.error(
                            "Unflare error: %s",
                            result.get("message", "Unknown error"),
                        )
                        return None

                    cookies = result.get("cookies", [])
                    unflare_headers = result.get("headers", {})
        except (aiohttp.ClientError, OSError) as e:
            logger.error("Unflare request failed: %s", e)
            return None

        # Cache the cookies and headers, then fulfil the request via the shared
        # replay path (single source of truth for header merging,
        # Accept-Encoding, and 403 -> cache-clear handling). Done after the
        # Unflare session closes so its connection is not held open across the
        # replay and its retries.
        self.cache_credentials(cookies, unflare_headers)
        return await self._try_cached_request(url, headers)
