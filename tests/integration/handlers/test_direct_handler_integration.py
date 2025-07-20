"""Integration tests for DirectRequestHandler."""
import pytest

from pro_sports_transactions.handlers import DirectRequestHandler
from pro_sports_transactions.search import headers


class TestDirectRequestHandlerIntegration:
    """Integration tests for DirectRequestHandler (expected to fail due to
    Cloudflare)"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_direct_request_blocked_by_cloudflare(self):
        """
        Test that direct requests to prosportstransactions.com are blocked by
        Cloudflare.
        This test documents the current state and confirms why we need proxy solutions.
        """
        handler = DirectRequestHandler()
        url = (
            "https://www.prosportstransactions.com/basketball/Search/"
            "SearchResults.php?BeginDate=2023-01-01&EndDate=2023-01-02&Submit=Search"
        )

        # This should return None due to Cloudflare JA4 protection
        result = await handler.get(url, headers)

        # Expected: Cloudflare blocks the request, returns None or error response
        # This confirms why we need UnflareRequestHandler
        assert result is None or "Cloudflare" in result or "403" in str(result)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_direct_request_to_other_site_works(self):
        """
        Test that DirectRequestHandler works fine with non-Cloudflare sites.
        This confirms the handler itself is functional.
        """
        handler = DirectRequestHandler()

        # Use a simple test endpoint that should work
        url = "https://httpbin.org/get"
        test_headers = {"User-Agent": "test-agent"}

        result = await handler.get(url, test_headers)

        # Should get a valid JSON response from httpbin
        assert result is not None
        assert "headers" in result  # httpbin returns request details including headers
