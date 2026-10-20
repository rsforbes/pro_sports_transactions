"""Integration tests for UnflareRequestHandler."""

import pytest

from pro_sports_transactions.handlers import UnflareConfig, UnflareRequestHandler
from pro_sports_transactions.search import headers

# A transaction type must be checked: without one the site returns a "No
# Transaction Type boxes were checked." page instead of results.
URL = (
    "https://www.prosportstransactions.com/basketball/Search/"
    "SearchResults.php?BeginDate=2023-01-01&EndDate=2023-01-31&Submit=Search"
    "&PlayerMovementChkBx=yes"
)

# The results table on a real (non-challenge) search page.
RESULTS_TABLE = '<table class="datatable center">'


class TestUnflareHandlerIntegration:
    """Integration tests for UnflareRequestHandler (requires Unflare service)"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unflare_request_with_service_check(self, unflare_config):
        """
        Test UnflareRequestHandler behavior with proper service availability check.
        Skips if service is not running, tests functionality if it is.
        """
        # This should work when Unflare service is running
        async with UnflareRequestHandler(unflare_config) as handler:
            result = await handler.get(URL, headers)

        # Should get the search results page when service is working
        assert result is not None
        assert RESULTS_TABLE in result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unflare_service_unavailable_scenario(self):
        """
        Test UnflareRequestHandler behavior when service is unavailable.
        Uses a non-existent URL to simulate service being down.
        """
        # Use non-existent URL to simulate service down
        config = UnflareConfig(url="http://localhost:9999/scrape")

        # Should return None when service is not available
        async with UnflareRequestHandler(config) as handler:
            result = await handler.get(URL, headers)
        assert result is None

    @pytest.mark.integration
    def test_unflare_config_customization(self):
        """Test that UnflareConfig can be customized for different setups"""
        # Custom configuration for different Unflare setup
        config = UnflareConfig(
            url="http://192.168.1.100:8080/scrape",
            timeout=30000,
            proxy={"host": "corporate-proxy.com", "port": 8080},
        )

        handler = UnflareRequestHandler(config)

        assert handler.config.url == "http://192.168.1.100:8080/scrape"
        assert handler.config.timeout == 30000
        assert handler.config.proxy["host"] == "corporate-proxy.com"
