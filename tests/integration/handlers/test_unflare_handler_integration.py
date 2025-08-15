"""Integration tests for UnflareRequestHandler."""
import asyncio

import aiohttp
import pytest

from pro_sports_transactions.handlers import (UnflareConfig,
                                              UnflareRequestHandler)
from pro_sports_transactions.search import headers


async def is_unflare_service_available(service_url: str) -> bool:
    """Check if Unflare service is running and accessible."""
    try:
        # Try to connect to the service with a minimal request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                service_url,
                json={"url": "https://example.com", "timeout": 5000},
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=2),
            ):
                # Service is running if we get any response (even error)
                return True
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return False


class TestUnflareHandlerIntegration:
    """Integration tests for UnflareRequestHandler (requires Unflare service)"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unflare_request_with_service_check(self):
        """
        Test UnflareRequestHandler behavior with proper service availability check.
        Skips if service is not running, tests functionality if it is.
        """
        config = UnflareConfig(
            url="http://localhost:5002/scrape"
        )  # Use host port from devcontainer

        # Check if service is available
        service_available = await is_unflare_service_available(config.url)

        if not service_available:
            pytest.skip("Unflare service not available - cannot test integration")

        # Service is available - test actual functionality
        handler = UnflareRequestHandler(config)

        url = (
            "https://www.prosportstransactions.com/basketball/Search/"
            "SearchResults.php?BeginDate=2023-01-01&EndDate=2023-01-02&Submit=Search"
        )

        # This should work when Unflare service is running
        result = await handler.get(url, headers)

        # Should get HTML content when service is working
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain expected HTML elements
        assert "prosportstransactions.com" in result.lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unflare_service_unavailable_scenario(self):
        """
        Test UnflareRequestHandler behavior when service is unavailable.
        Uses a non-existent URL to simulate service being down.
        """
        # Use non-existent URL to simulate service down
        config = UnflareConfig(url="http://localhost:9999/scrape")
        handler = UnflareRequestHandler(config)

        url = (
            "https://www.prosportstransactions.com/basketball/Search/"
            "SearchResults.php?BeginDate=2023-01-01&EndDate=2023-01-02&Submit=Search"
        )

        # Should return None when service is not available
        result = await handler.get(url, headers)
        assert result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unflare_request_with_docker_service(self):
        """
        Test UnflareRequestHandler with Docker-hosted Unflare service.
        Skips if Docker service is not available.
        """
        config = UnflareConfig(url="http://host.docker.internal:5002/scrape")

        # Check if Docker-hosted service is available
        service_available = await is_unflare_service_available(config.url)

        if not service_available:
            pytest.skip("Docker-hosted Unflare service not available")

        handler = UnflareRequestHandler(config)

        url = (
            "https://www.prosportstransactions.com/basketball/Search/"
            "SearchResults.php?BeginDate=2023-01-01&EndDate=2023-01-02&Submit=Search"
        )

        result = await handler.get(url, headers)

        # When Unflare service is running, should get HTML content
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

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
