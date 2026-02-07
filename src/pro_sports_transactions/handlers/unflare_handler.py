"""Unflare proxy request handler for bypassing Cloudflare protection."""

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

import aiohttp

from .base_handler import RequestConfig, RequestHandler

logger = logging.getLogger(__name__)


@dataclass
class UnflareConfig(RequestConfig):
    """Configuration for Unflare proxy requests"""

    url: str = "http://localhost:5002/scrape"
    timeout: int = 60000
    proxy: Optional[Dict[str, any]] = None


class UnflareRequestHandler(RequestHandler):
    """Unflare proxy request handler for bypassing Cloudflare"""

    def __init__(self, config: UnflareConfig):
        self.config = config
        self._cached_cookies = None
        self._cached_headers = None
        self._cache_expiry = 0

    async def get(self, url: str, headers: Dict[str, str]) -> Optional[str]:
        # Check if we have valid cached cookies
        if self.is_cache_valid():
            result = await self._try_cached_request(url, headers)
            if result is not None:
                return result

        # Cache miss or expired - get fresh cookies from Unflare
        return await self._refresh_cache_and_request(url, headers)

    def is_cache_valid(self) -> bool:
        """Check if cached cookies are still valid.

        Returns:
            True if cache is valid and not expired, False otherwise
        """
        return (
            self._cached_cookies is not None
            and self._cached_headers is not None
            and time.time() < self._cache_expiry
        )

    async def _try_cached_request(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Try to make request using cached cookies"""
        try:
            logger.info("Requesting with cached credentials")
            final_headers = {**headers, **self._cached_headers}
            final_headers["Accept-Encoding"] = "gzip, deflate, br"
            if self._cached_cookies:
                final_headers["Cookie"] = self._cached_cookies

            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(
                headers=final_headers, timeout=timeout
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text(encoding="utf-8")
                    if response.status == 403:
                        # Cloudflare challenge - cookies expired
                        logger.warning("Cached cookies expired, refreshing...")
                        self.clear_cache()
                        return None
                    logger.warning(
                        "Cached request failed with status %d: %s",
                        response.status,
                        await response.text(),
                    )
                    return None
        except (aiohttp.ClientError, OSError) as e:
            logger.error("Cached request failed: %s", e)
            return None

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

                    # Cache the cookies and headers
                    self.cache_credentials(cookies, unflare_headers)

                    # Build final headers
                    final_headers = {**headers, **unflare_headers}
                    final_headers["Accept-Encoding"] = "gzip, deflate, br"
                    if self._cached_cookies:
                        final_headers["Cookie"] = self._cached_cookies

                    # Make the actual request
                    async with aiohttp.ClientSession(
                        headers=final_headers, timeout=timeout
                    ) as final_session:
                        async with final_session.get(url) as final_response:
                            if final_response.status != 200:
                                logger.warning(
                                    "Final request failed with status %d: %s",
                                    final_response.status,
                                    await final_response.text(),
                                )
                                return None
                            return await final_response.text(encoding="utf-8")
        except (aiohttp.ClientError, OSError) as e:
            logger.error("Unflare request failed: %s", e)
            return None

    def cache_credentials(self, cookies: list, unflare_headers: dict):
        """Cache cookies and headers with expiration.

        Args:
            cookies: List of cookie dictionaries from Unflare response
            unflare_headers: Headers dictionary from Unflare response

        Useful for manually managing cache or pre-warming credentials.
        """
        # Build cookie header
        self._cached_cookies = (
            "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
            if cookies
            else None
        )

        self._cached_headers = unflare_headers

        # Set cache expiry (use earliest cookie expiry or default to 1 hour)
        min_expiry = time.time() + 3600  # Default 1 hour
        for cookie in cookies:
            if "expires" in cookie:
                min_expiry = min(min_expiry, cookie["expires"])

        # Add some buffer (5 minutes before actual expiry)
        self._cache_expiry = min_expiry - 300

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
