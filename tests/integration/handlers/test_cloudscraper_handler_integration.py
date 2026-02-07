"""Integration tests for CloudscraperRequestHandler."""

import pytest

from pro_sports_transactions.handlers import (CloudscraperConfig,
                                              CloudscraperRequestHandler)
from pro_sports_transactions.search import headers


class TestCloudscraperHandlerIntegration:
    """Integration tests for CloudscraperRequestHandler."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_request_to_prosportstransactions(self):
        """
        Test CloudscraperRequestHandler against prosportstransactions.com.

        Fails if cloudscraper cannot bypass Cloudflare, which signals
        that the library may need updating or an alternative approach.
        """
        handler = CloudscraperRequestHandler()

        url = (
            "https://www.prosportstransactions.com/basketball/Search/"
            "SearchResults.php?"
            "BeginDate=2023-01-01&EndDate=2023-01-02"
            "&Submit=Search"
        )

        result = await handler.get(url, headers)

        assert result is not None, (
            "Cloudscraper failed to bypass Cloudflare. "
            "The library may need updating."
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_request_with_custom_config(self):
        """
        Test CloudscraperRequestHandler with custom config against
        prosportstransactions.com.

        Validates that a handler with non-default config can still
        bypass Cloudflare and return content.
        """
        config = CloudscraperConfig(browser="chrome", delay=10)
        handler = CloudscraperRequestHandler(config)

        url = (
            "https://www.prosportstransactions.com/football/Search/"
            "SearchResults.php?"
            "BeginDate=2023-06-01&EndDate=2023-06-02"
            "&Submit=Search"
        )

        result = await handler.get(url, headers)

        assert result is not None, (
            "Cloudscraper failed to bypass Cloudflare. "
            "The library may need updating."
        )
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.integration
    def test_cloudscraper_config_customization(self):
        """Test that CloudscraperConfig can be customized."""
        config = CloudscraperConfig(
            browser="firefox",
            delay=10,
            interpreter="nodejs",
        )

        handler = CloudscraperRequestHandler(config)

        assert handler.config.browser == "firefox"
        assert handler.config.delay == 10
        assert handler.config.interpreter == "nodejs"
