"""Unit tests for unflare handling."""
import time
from unittest.mock import AsyncMock, patch

import pytest

from pro_sports_transactions.handlers import (UnflareConfig,
                                              UnflareRequestHandler)


class TestUnflareHandler:
    """Test the UnflareRequestHandler"""

    @pytest.mark.unit
    def test_config_defaults(self):
        """Test UnflareConfig default values"""
        config = UnflareConfig()

        assert config.url == "http://localhost:5002/scrape"
        assert config.timeout == 60000
        assert config.proxy is None

    @pytest.mark.unit
    def test_config_custom_values(self):
        """Test UnflareConfig with custom values"""
        config = UnflareConfig(
            url="http://custom:8080/scrape",
            timeout=30000,
            proxy={"host": "proxy.com", "port": 8080},
        )

        assert config.url == "http://custom:8080/scrape"
        assert config.timeout == 30000
        assert config.proxy == {"host": "proxy.com", "port": 8080}

    @pytest.mark.unit
    def test_handler_initialization(self):
        """Test handler initialization"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        assert handler.config == config
        assert not handler.has_cached_cookies
        assert handler.cache_expiry_time == 0

    @pytest.mark.unit
    def test_cache_validity_empty(self):
        """Test cache validity when cache is empty"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        assert not handler.is_cache_valid()

    @pytest.mark.unit
    def test_cache_validity_expired(self):
        """Test cache validity when cache is expired"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        # Set expired cache by directly calling cache_credentials with expired data
        expired_cookies = [
            {"name": "test", "value": "value", "expires": time.time() - 100}
        ]
        handler.cache_credentials(expired_cookies, {"X-Test": "value"})

        assert not handler.is_cache_valid()

    @pytest.mark.unit
    def test_cache_validity_valid(self):
        """Test cache validity when cache is valid"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        # Set valid cache by calling cache_credentials with future expiry
        # (need extra time for 5min buffer)
        valid_cookies = [
            {"name": "test", "value": "value", "expires": time.time() + 1000}
        ]
        handler.cache_credentials(valid_cookies, {"X-Test": "value"})

        assert handler.is_cache_valid()

    @pytest.mark.unit
    def test_cache_credentials(self):
        """Test caching of cookies and headers"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        cookies = [
            {"name": "session", "value": "abc123", "expires": time.time() + 3600},
            {"name": "csrf", "value": "xyz789", "expires": time.time() + 1800},
        ]
        headers = {"X-Unflare": "test", "X-CF-Ray": "12345"}

        handler.cache_credentials(cookies, headers)

        assert handler.has_cached_cookies
        assert handler.cache_expiry_time > 0

    @pytest.mark.unit
    def test_clear_cache(self):
        """Test clearing the cache"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        # Set some cache data
        test_cookies = [
            {"name": "test", "value": "value", "expires": time.time() + 100}
        ]
        handler.cache_credentials(test_cookies, {"X-Test": "value"})

        handler.clear_cache()

        assert not handler.has_cached_cookies
        assert handler.cache_expiry_time == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_with_no_cache(self):
        """Test get request when no cache exists"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        # Mock the refresh_cache_and_request method
        with patch.object(
            handler, "_refresh_cache_and_request", new_callable=AsyncMock
        ) as mock_refresh:
            mock_refresh.return_value = "<html>Fresh Response</html>"

            result = await handler.get("http://example.com", {"test": "header"})

            assert result == "<html>Fresh Response</html>"
            mock_refresh.assert_called_once_with(
                "http://example.com", {"test": "header"}
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_with_valid_cache(self):
        """Test get request when valid cache exists"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        # Set valid cache (need extra time for 5min buffer)
        valid_cookies = [
            {"name": "session", "value": "abc123", "expires": time.time() + 1000}
        ]
        handler.cache_credentials(valid_cookies, {"X-CF-Ray": "12345"})

        # Mock the try_cached_request method
        with patch.object(
            handler, "_try_cached_request", new_callable=AsyncMock
        ) as mock_cached:
            mock_cached.return_value = "<html>Cached Response</html>"

            result = await handler.get("http://example.com", {"test": "header"})

            assert result == "<html>Cached Response</html>"
            mock_cached.assert_called_once_with(
                "http://example.com", {"test": "header"}
            )
