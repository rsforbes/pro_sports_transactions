"""Unflare proxy request handler for bypassing Cloudflare protection."""
import time
from dataclasses import dataclass
from typing import Dict, Optional

import aiohttp

from .base_handler import RequestConfig, RequestHandler


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
            self._cached_cookies is not None and
            self._cached_headers is not None and
            time.time() < self._cache_expiry
        )

    async def _try_cached_request(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Try to make request using cached cookies"""
        try:
            print("Using cached cookies (fast path)")
            final_headers = {**headers, **self._cached_headers}
            if self._cached_cookies:
                final_headers["Cookie"] = self._cached_cookies

            async with aiohttp.ClientSession(headers=final_headers) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text(encoding="utf-8")
                    if response.status == 403:
                        # Cloudflare challenge - cookies expired
                        print("Cached cookies expired, refreshing...")
                        self.clear_cache()
                        return None
                    return None
        except (aiohttp.ClientError, OSError) as e:
            print(f"Cached request failed: {e}")
            return None

    async def _refresh_cache_and_request(
        self, url: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Get fresh cookies from Unflare and cache them"""
        print("Requesting fresh cookies from Unflare (slow path)")
        request_data = {"url": url, "timeout": self.config.timeout, "method": "GET"}

        if self.config.proxy:
            request_data["proxy"] = self.config.proxy

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.url,
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status != 200:
                        return None

                    result = await response.json()

                    if "code" in result and result["code"] == "error":
                        print(
                            f"Unflare error: {result.get('message', 'Unknown error')}"
                        )
                        return None

                    cookies = result.get("cookies", [])
                    unflare_headers = result.get("headers", {})

                    # Cache the cookies and headers
                    self.cache_credentials(cookies, unflare_headers)

                    # Build final headers
                    final_headers = {**headers, **unflare_headers}
                    if self._cached_cookies:
                        final_headers["Cookie"] = self._cached_cookies

                    # Make the actual request
                    async with aiohttp.ClientSession(
                        headers=final_headers
                    ) as final_session:
                        async with final_session.get(url) as final_response:
                            return (
                                None
                                if final_response.status != 200
                                else await final_response.text(encoding="utf-8")
                            )
        except (aiohttp.ClientError, OSError) as e:
            print(f"Unflare request failed: {e}")
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
