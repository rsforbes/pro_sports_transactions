"""
Simplified Playwright client without complex anti-detection measures.
Focus on basic functionality that works reliably.
"""

import asyncio
from typing import Dict, Optional

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None


class SimplePlaywrightClient:
    """Simplified Playwright client focused on reliability"""

    def __init__(self):
        if async_playwright is None:
            raise ImportError("Playwright not installed")

    async def _setup_browser_context(self, playwright):
        """Set up browser context with anti-detection settings."""
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        return browser, context

    async def _navigate_and_wait(self, page, url):
        """Navigate to page and handle Cloudflare protection."""
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        title = await page.title()
        if "just a moment" in title.lower():
            await asyncio.sleep(10)
            try:
                await page.wait_for_function(
                    "() => !document.title.toLowerCase()." "includes('just a moment')",
                    timeout=30000,
                )
            except Exception:
                pass
        return title

    async def _extract_table_data(self, tables):
        """Extract transaction data from tables."""
        transactions = []
        pages = 0

        if not tables:
            return transactions, pages

        # Extract from the first table
        rows = await tables[0].query_selector_all("tr")
        for row in rows[1:]:  # Skip header row
            cells = await row.query_selector_all("td")
            if len(cells) >= 5:
                cell_texts = await self._extract_cell_texts(cells)
                transaction = {
                    "Date": cell_texts[0],
                    "Team": cell_texts[1],
                    "Acquired": cell_texts[2],
                    "Relinquished": cell_texts[3],
                    "Notes": cell_texts[4],
                }
                transactions.append(transaction)

        # Extract page count from second table
        if len(tables) > 1:
            pages = await self._extract_page_count(tables[1])

        return transactions, pages

    async def _extract_cell_texts(self, cells):
        """Extract text content from table cells."""
        cell_texts = []
        for cell in cells:
            text = await cell.text_content()
            cell_texts.append(text.strip() if text else "")
        return cell_texts

    async def _extract_page_count(self, table):
        """Extract page count from pagination table."""
        try:
            page_text = await table.text_content()
            if page_text and "page" in page_text.lower():
                import re

                match = re.search(r"page \d+ of (\d+)", page_text.lower())
                if match:
                    return int(match.group(1))
        except Exception:
            pass
        return 0

    async def extract_transactions(self, url: str) -> Dict:
        """Extract transaction data from prosportstransactions.com"""
        async with async_playwright() as playwright:
            browser, context = await self._setup_browser_context(playwright)

            try:
                page = await context.new_page()
                title = await self._navigate_and_wait(page, url)

                # Extract transactions
                transactions = []
                pages = 0

                try:
                    tables = await page.query_selector_all("table")
                    transactions, pages = await self._extract_table_data(tables)
                except Exception as e:
                    print(f"Error extracting transactions: {e}")

                return {
                    "transactions": transactions,
                    "pages": pages,
                    "url": url,
                    "title": title,
                }

            finally:
                await browser.close()

    async def get_page_content(self, url: str) -> Optional[str]:
        """Get raw page content"""
        result = await self.extract_transactions(url)

        if result and result.get("transactions"):
            # Convert to HTML table format
            html = (
                "<table><tr><th>Date</th><th>Team</th><th>Acquired</th>"
                "<th>Relinquished</th><th>Notes</th></tr>"
            )
            for t in result["transactions"]:
                row = (
                    f"<tr><td>{t['Date']}</td><td>{t['Team']}</td>"
                    f"<td>{t['Acquired']}</td><td>{t['Relinquished']}</td>"
                    f"<td>{t['Notes']}</td></tr>"
                )
                html += row
            html += "</table>"

            # Add page info
            pages = result.get("pages", 0)
            pages_html = (
                f"<table><tr><td></td><td></td>"
                f"<td>Page 1 of {pages}</td></tr></table>"
            )
            html += pages_html

            return html

        return None
