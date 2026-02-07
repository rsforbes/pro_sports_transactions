"""Unit tests for unflare handling."""

import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
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

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_logs_non_200_unflare_response(self, caplog):
        """Test that non-200 from Unflare service is logged"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        mock_response = AsyncMock()
        mock_response.status = 502
        mock_response.text = AsyncMock(return_value="Bad Gateway")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with caplog.at_level(logging.WARNING):
                result = await handler._refresh_cache_and_request(
                    "http://example.com", {}
                )

        assert result is None
        assert "Unflare service returned status 502" in caplog.text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_logs_non_200_final_response(self, caplog):
        """Test that non-200 from the final request is logged"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        # Mock Unflare response (success)
        unflare_response = AsyncMock()
        unflare_response.status = 200
        unflare_response.json = AsyncMock(
            return_value={
                "cookies": [
                    {"name": "cf", "value": "abc", "expires": time.time() + 3600}
                ],
                "headers": {"X-CF": "test"},
            }
        )
        unflare_response.__aenter__ = AsyncMock(return_value=unflare_response)
        unflare_response.__aexit__ = AsyncMock(return_value=False)

        # Mock final response (failure)
        final_response = AsyncMock()
        final_response.status = 503
        final_response.text = AsyncMock(return_value="Service Unavailable")
        final_response.__aenter__ = AsyncMock(return_value=final_response)
        final_response.__aexit__ = AsyncMock(return_value=False)

        # First session (Unflare), second session (final request)
        unflare_session = AsyncMock()
        unflare_session.post = MagicMock(return_value=unflare_response)
        unflare_session.__aenter__ = AsyncMock(return_value=unflare_session)
        unflare_session.__aexit__ = AsyncMock(return_value=False)

        final_session = AsyncMock()
        final_session.get = MagicMock(return_value=final_response)
        final_session.__aenter__ = AsyncMock(return_value=final_session)
        final_session.__aexit__ = AsyncMock(return_value=False)

        sessions = [unflare_session, final_session]
        with patch("aiohttp.ClientSession", side_effect=sessions):
            with caplog.at_level(logging.WARNING):
                result = await handler._refresh_cache_and_request(
                    "http://example.com", {}
                )

        assert result is None
        assert "Final request failed with status 503" in caplog.text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cached_request_logs_non_200_response(self, caplog):
        """Test that non-200 from cached request is logged"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        # Set up valid cache
        valid_cookies = [
            {"name": "session", "value": "abc", "expires": time.time() + 1000}
        ]
        handler.cache_credentials(valid_cookies, {"X-CF": "test"})

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with caplog.at_level(logging.WARNING):
                result = await handler._try_cached_request("http://example.com", {})

        assert result is None
        assert "Cached request failed with status 500" in caplog.text

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sessions_use_timeout(self):
        """Test that aiohttp sessions are configured with a timeout"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "cookies": [
                    {"name": "cf", "value": "abc", "expires": time.time() + 3600}
                ],
                "headers": {"X-CF": "test"},
            }
        )
        mock_response.text = AsyncMock(return_value="<html>OK</html>")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session) as mock_cls:
            await handler._refresh_cache_and_request("http://example.com", {})

            # All ClientSession calls should include a timeout
            for call in mock_cls.call_args_list:
                _, kwargs = call
                assert "timeout" in kwargs
                assert isinstance(kwargs["timeout"], aiohttp.ClientTimeout)
                assert kwargs["timeout"].total == 120

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sessions_include_accept_encoding(self):
        """Test that final request sessions include Accept-Encoding header"""
        config = UnflareConfig()
        handler = UnflareRequestHandler(config)

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "cookies": [
                    {"name": "cf", "value": "abc", "expires": time.time() + 3600}
                ],
                "headers": {"X-CF": "test"},
            }
        )
        mock_response.text = AsyncMock(return_value="<html>OK</html>")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session) as mock_cls:
            await handler._refresh_cache_and_request(
                "http://example.com", {"User-Agent": "test"}
            )

            # The final session (second call) should have Accept-Encoding in headers
            final_call = mock_cls.call_args_list[-1]
            _, kwargs = final_call
            assert "headers" in kwargs
            assert kwargs["headers"]["Accept-Encoding"] == "gzip, deflate, br"
