"""Unit tests for DirectRequestHandler."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pro_sports_transactions.handlers import DirectRequestHandler


class TestDirectRequestHandler:
    """Test the DirectRequestHandler"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test successful HTTP request"""
        handler = DirectRequestHandler()

        # Mock the entire aiohttp module
        with patch(
            "pro_sports_transactions.handlers.direct_handler.aiohttp"
        ) as mock_aiohttp:
            # Create mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="<html>Test Response</html>")

            # Create properly configured async context manager for session.get()
            mock_get_context = AsyncMock()
            mock_get_context.__aenter__.return_value = mock_response
            mock_get_context.__aexit__.return_value = None

            # Create mock session with properly configured get method
            mock_session = MagicMock()
            mock_session.get.return_value = mock_get_context

            # Configure ClientSession mock
            mock_aiohttp.ClientSession.return_value.__aenter__.return_value = (
                mock_session
            )

            result = await handler.get("http://example.com", {"test": "header"})

            assert result == "<html>Test Response</html>"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failed_request(self):
        """Test failed HTTP request (non-200 status)"""
        handler = DirectRequestHandler()

        with patch(
            "pro_sports_transactions.handlers.direct_handler.aiohttp"
        ) as mock_aiohttp:
            # Create mock response with 404 status
            mock_response = MagicMock()
            mock_response.status = 404

            # Create properly configured async context manager for session.get()
            mock_get_context = AsyncMock()
            mock_get_context.__aenter__.return_value = mock_response
            mock_get_context.__aexit__.return_value = None

            # Create mock session with properly configured get method
            mock_session = MagicMock()
            mock_session.get.return_value = mock_get_context

            # Configure ClientSession mock
            mock_aiohttp.ClientSession.return_value.__aenter__.return_value = (
                mock_session
            )

            result = await handler.get("http://example.com", {"test": "header"})

            assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_headers_passed_correctly(self):
        """Test that headers are passed to aiohttp session"""
        handler = DirectRequestHandler()
        headers = {"User-Agent": "test-agent", "Authorization": "Bearer token"}

        with patch(
            "pro_sports_transactions.handlers.direct_handler.aiohttp"
        ) as mock_aiohttp:
            # Create mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="success")

            # Create properly configured async context manager for session.get()
            mock_get_context = AsyncMock()
            mock_get_context.__aenter__.return_value = mock_response
            mock_get_context.__aexit__.return_value = None

            # Create mock session with properly configured get method
            mock_session = MagicMock()
            mock_session.get.return_value = mock_get_context

            # Configure ClientSession mock
            mock_aiohttp.ClientSession.return_value.__aenter__.return_value = (
                mock_session
            )

            await handler.get("http://example.com", headers)

            # Verify session was created with correct headers
            mock_aiohttp.ClientSession.assert_called_once_with(headers=headers)
