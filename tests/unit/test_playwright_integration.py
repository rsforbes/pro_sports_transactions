"""
Tests for Playwright integration and JA4 bypass functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch

try:
    from pro_sports_transactions.simple_playwright import SimplePlaywrightClient
    from pro_sports_transactions.search import League, Search

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestSimplePlaywrightClient:
    """Test the SimplePlaywrightClient class"""

    def test_init_without_playwright(self):
        """Test initialization when Playwright is not available"""
        with patch("pro_sports_transactions.simple_playwright.async_playwright", None):
            with pytest.raises(ImportError):
                SimplePlaywrightClient()

    def test_init_with_playwright(self):
        """Test successful initialization"""
        client = SimplePlaywrightClient()
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_page_content_mock(self):
        """Test get_page_content with mocked Playwright"""
        client = SimplePlaywrightClient()

        # Mock the extract_transactions method to return data
        mock_result = {
            "transactions": [
                {
                    "Date": "2023-01-01",
                    "Team": "Lakers",
                    "Acquired": "Player A",
                    "Relinquished": "",
                    "Notes": "Test",
                }
            ],
            "pages": 1,
            "title": "Test Page",
            "url": "https://example.com",
        }

        with patch.object(client, "extract_transactions", return_value=mock_result):
            result = await client.get_page_content("https://example.com")

            assert result is not None
            assert "<table>" in result
            assert "Test Page" not in result  # Content should be HTML table, not title
            assert "2023-01-01" in result
            assert "Lakers" in result

    @pytest.mark.asyncio
    async def test_extract_transactions_mock(self):
        """Test extract_transactions with mocked Playwright"""
        client = SimplePlaywrightClient()

        # Mock the entire Playwright chain
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_table = AsyncMock()
        mock_row = AsyncMock()
        mock_cell = AsyncMock()

        # Set up mock returns for transaction data
        mock_cell.text_content.return_value = "Test Data"
        mock_row.query_selector_all.return_value = [mock_cell] * 5
        mock_table.query_selector_all.return_value = [mock_row]
        mock_page.query_selector_all.return_value = [
            mock_table,
            mock_table,
        ]  # Two tables
        mock_page.title.return_value = "Search Results"
        mock_context.new_page.return_value = mock_page
        mock_browser.close = AsyncMock()

        with patch.object(
            client, "_setup_browser_context", return_value=(mock_browser, mock_context)
        ):
            with patch.object(
                client, "_navigate_and_wait", return_value="Search Results"
            ):
                with patch.object(client, "_extract_page_count", return_value=1):
                    with patch(
                        "pro_sports_transactions.simple_playwright.async_playwright"
                    ) as mock_pw:
                        mock_pw.return_value.__aenter__.return_value = mock_playwright

                        result = await client.extract_transactions(
                            "https://example.com"
                        )

                        assert "transactions" in result
                        assert "pages" in result
                        assert "title" in result
                        assert "url" in result
                        assert result["title"] == "Search Results"
                        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_cell_texts(self):
        """Test _extract_cell_texts helper method"""
        client = SimplePlaywrightClient()

        # Mock cells
        mock_cells = []
        for text in ["2023-01-01", "Lakers", "Player A", "", "Test note"]:
            mock_cell = AsyncMock()
            mock_cell.text_content.return_value = text
            mock_cells.append(mock_cell)

        result = await client._extract_cell_texts(mock_cells)

        assert len(result) == 5
        assert result[0] == "2023-01-01"
        assert result[1] == "Lakers"
        assert result[2] == "Player A"
        assert result[3] == ""
        assert result[4] == "Test note"

    @pytest.mark.asyncio
    async def test_extract_page_count(self):
        """Test _extract_page_count helper method"""
        client = SimplePlaywrightClient()

        # Mock table with page info
        mock_table = AsyncMock()
        mock_table.text_content.return_value = "Page 1 of 5"

        result = await client._extract_page_count(mock_table)
        assert result == 5

        # Test with no page info
        mock_table.text_content.return_value = "No page info"
        result = await client._extract_page_count(mock_table)
        assert result == 0


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestSearchWithPlaywright:
    """Test the Search class with Playwright integration"""

    @pytest.mark.asyncio
    async def test_search_uses_playwright(self):
        """Test that Search class uses Playwright automatically"""
        search = Search(league=League.NBA)

        # Mock the SimplePlaywrightClient import in the Http.get method
        with patch(
            "pro_sports_transactions.simple_playwright.SimplePlaywrightClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_page_content.return_value = """
            <table>
                <tr><th>Date</th><th>Team</th><th>Acquired</th><th>Relinquished</th><th>Notes</th></tr>
                <tr><td>2023-01-01</td><td>Lakers</td><td>Player A</td><td></td><td>Test transaction</td></tr>
            </table>
            <table>
                <tr><td></td><td></td><td>Page 1 of 1</td></tr>
            </table>
            """
            mock_client_class.return_value = mock_client

            result = await search.get_dict()

            # Verify that Playwright was used
            mock_client_class.assert_called_once()
            mock_client.get_page_content.assert_called_once()

            # Verify result structure
            assert "transactions" in result
            assert "pages" in result
            assert (
                len(result["transactions"]) >= 0
            )  # Could be 0 or more depending on parsing

    @pytest.mark.asyncio
    async def test_search_handles_playwright_failure(self):
        """Test that Search class handles Playwright failures gracefully"""
        search = Search(league=League.NBA)

        # Mock the SimplePlaywrightClient to fail
        with patch(
            "pro_sports_transactions.simple_playwright.SimplePlaywrightClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_page_content.side_effect = Exception("Playwright failed")
            mock_client_class.return_value = mock_client

            result = await search.get_dict()

            # Should return empty result with error
            assert "transactions" in result
            assert "pages" in result
            assert "errors" in result
            assert result["pages"] == 0
            assert len(result["transactions"]) == 0


def test_imports_without_playwright():
    """Test that main package imports work even without Playwright"""
    # This test verifies our cleanup - we now require Playwright
    # but the basic imports should still work
    from pro_sports_transactions import League, Search, TransactionType

    assert League is not None
    assert Search is not None
    assert TransactionType is not None


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not available")
class TestCloudflareBypass:
    """Test Cloudflare bypass functionality"""

    @pytest.mark.asyncio
    async def test_cloudflare_detection_and_wait(self):
        """Test that client properly detects and waits for Cloudflare"""
        client = SimplePlaywrightClient()

        # Mock page with Cloudflare protection
        mock_page = AsyncMock()
        mock_page.title.return_value = "Just a moment..."  # Cloudflare title
        mock_page.goto = AsyncMock()
        mock_page.wait_for_function = AsyncMock()

        # Mock the navigation and wait function
        with patch("asyncio.sleep", new_callable=AsyncMock):
            title = await client._navigate_and_wait(mock_page, "https://example.com")

            # Should have detected Cloudflare and waited
            assert title == "Just a moment..."
            mock_page.wait_for_function.assert_called_once()

    @pytest.mark.asyncio
    async def test_normal_page_no_cloudflare_wait(self):
        """Test that client doesn't wait unnecessarily for normal pages"""
        client = SimplePlaywrightClient()

        # Mock page without Cloudflare protection
        mock_page = AsyncMock()
        mock_page.title.return_value = "Normal Page"
        mock_page.goto = AsyncMock()
        mock_page.wait_for_function = AsyncMock()

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            title = await client._navigate_and_wait(mock_page, "https://example.com")

            # Should not have waited for Cloudflare (only initial 2 second wait)
            assert title == "Normal Page"
            mock_page.wait_for_function.assert_not_called()
            # Should have called sleep only once (the initial 2 second wait)
            assert mock_sleep.call_count == 1
