"""Unit tests for cloudscraper handling."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from pro_sports_transactions.handlers import (CloudscraperConfig,
                                              CloudscraperRequestHandler)


class TestCloudscraperConfig:
    """Test CloudscraperConfig defaults and customization."""

    @pytest.mark.unit
    def test_config_defaults(self):
        """Test CloudscraperConfig default values."""
        config = CloudscraperConfig()

        assert config.browser == "chrome"
        assert config.delay == 5
        assert config.interpreter == "native"
        assert config.captcha is None

    @pytest.mark.unit
    def test_config_custom_values(self):
        """Test CloudscraperConfig with custom values."""
        config = CloudscraperConfig(
            browser="firefox",
            delay=10,
            interpreter="nodejs",
            captcha={"provider": "2captcha", "api_key": "test"},
        )

        assert config.browser == "firefox"
        assert config.delay == 10
        assert config.interpreter == "nodejs"
        assert config.captcha == {"provider": "2captcha", "api_key": "test"}


class TestCloudscraperHandler:
    """Test the CloudscraperRequestHandler."""

    @pytest.mark.unit
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    def test_handler_init_default_config(self, mock_create):
        """Test handler initialization with default config."""
        mock_create.return_value = MagicMock()
        handler = CloudscraperRequestHandler()

        assert handler.config.browser == "chrome"
        assert handler.config.delay == 5
        mock_create.assert_called_once_with(
            browser={"browser": "chrome"},
            delay=5,
            interpreter="native",
        )

    @pytest.mark.unit
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    def test_handler_init_custom_config(self, mock_create):
        """Test handler initialization with custom config."""
        mock_create.return_value = MagicMock()
        config = CloudscraperConfig(browser="firefox", delay=10, interpreter="nodejs")
        handler = CloudscraperRequestHandler(config)

        assert handler.config == config
        mock_create.assert_called_once_with(
            browser={"browser": "firefox"},
            delay=10,
            interpreter="nodejs",
        )

    @pytest.mark.unit
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    def test_handler_init_with_captcha(self, mock_create):
        """Test handler initialization with captcha config."""
        mock_create.return_value = MagicMock()
        captcha_config = {"provider": "2captcha", "api_key": "test_key"}
        config = CloudscraperConfig(captcha=captcha_config)
        CloudscraperRequestHandler(config)

        mock_create.assert_called_once_with(
            browser={"browser": "chrome"},
            delay=5,
            interpreter="native",
            captcha=captcha_config,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    async def test_successful_request(self, mock_create):
        """Test successful request returns response text."""
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Success</html>"
        mock_scraper.get.return_value = mock_response
        mock_create.return_value = mock_scraper

        handler = CloudscraperRequestHandler()
        result = await handler.get("http://example.com", {"User-Agent": "test"})

        assert result == "<html>Success</html>"
        mock_scraper.get.assert_called_once_with(
            "http://example.com", headers={"User-Agent": "test"}
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    async def test_non_200_returns_none(self, mock_create):
        """Test non-200 response returns None."""
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_scraper.get.return_value = mock_response
        mock_create.return_value = mock_scraper

        handler = CloudscraperRequestHandler()
        result = await handler.get("http://example.com", {})

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    async def test_non_200_logs_warning(self, mock_create, caplog):
        """Test non-200 response logs a warning."""
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_scraper.get.return_value = mock_response
        mock_create.return_value = mock_scraper

        handler = CloudscraperRequestHandler()
        with caplog.at_level(logging.WARNING):
            await handler.get("http://example.com", {})

        assert "Cloudscraper request returned status 503" in caplog.text

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    async def test_exception_returns_none(self, mock_create):
        """Test exception during request returns None."""
        mock_scraper = MagicMock()
        mock_scraper.get.side_effect = Exception("Connection failed")
        mock_create.return_value = mock_scraper

        handler = CloudscraperRequestHandler()
        result = await handler.get("http://example.com", {})

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    async def test_exception_logs_error(self, mock_create, caplog):
        """Test exception during request logs an error."""
        mock_scraper = MagicMock()
        mock_scraper.get.side_effect = Exception("Connection failed")
        mock_create.return_value = mock_scraper

        handler = CloudscraperRequestHandler()
        with caplog.at_level(logging.ERROR):
            await handler.get("http://example.com", {})

        assert "Cloudscraper request failed" in caplog.text
        assert "Connection failed" in caplog.text

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    async def test_headers_forwarded(self, mock_create):
        """Test that headers are forwarded to the scraper."""
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_scraper.get.return_value = mock_response
        mock_create.return_value = mock_scraper

        custom_headers = {
            "User-Agent": "Custom/1.0",
            "Accept": "text/html",
            "X-Custom": "value",
        }

        handler = CloudscraperRequestHandler()
        await handler.get("http://example.com", custom_headers)

        mock_scraper.get.assert_called_once_with(
            "http://example.com", headers=custom_headers
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch(
        "pro_sports_transactions.handlers.cloudscraper_handler.cloudscraper.create_scraper"
    )
    async def test_info_log_on_request(self, mock_create, caplog):
        """Test that an info log is emitted for each request."""
        mock_scraper = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_scraper.get.return_value = mock_response
        mock_create.return_value = mock_scraper

        handler = CloudscraperRequestHandler()
        with caplog.at_level(logging.INFO):
            await handler.get("http://example.com/test", {})

        assert "Requesting http://example.com/test via cloudscraper" in caplog.text
