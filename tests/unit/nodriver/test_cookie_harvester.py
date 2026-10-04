"""Unit tests for CookieHarvester."""

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pro_sports_transactions.nodriver import CookieHarvester

URL = "https://www.prosportstransactions.com/basketball/Search/SearchResults.php"


class TestCookieHarvester:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("host", "domain", "expected"),
        [
            ("www.prosportstransactions.com", ".prosportstransactions.com", True),
            ("www.prosportstransactions.com", "www.prosportstransactions.com", True),
            ("WWW.ProSportsTransactions.com", "prosportstransactions.com", True),
            ("www.prosportstransactions.com", "example.com", False),
            # Substring of the host but NOT a domain suffix.
            ("www.prosportstransactions.com", "sportstransactions.com", False),
            ("www.prosportstransactions.com", "", False),
        ],
    )
    def test_host_matches(self, host, domain, expected):
        assert CookieHarvester.host_matches(host, domain) is expected

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_harvest_filters_by_host_and_formats(self):
        cookies = [
            SimpleNamespace(
                name="cf_clearance",
                value="tok",
                domain=".prosportstransactions.com",
                expires=time.time() + 3600,
            ),
            SimpleNamespace(name="other", value="x", domain=".example.com", expires=-1),
            SimpleNamespace(name="session", value="s", domain="", expires=-1),
            SimpleNamespace(
                name="substring", value="z", domain="sportstransactions.com", expires=-1
            ),
            SimpleNamespace(name="", value="v", domain="", expires=-1),
        ]
        browser = MagicMock()
        browser.cookies.get_all = AsyncMock(return_value=cookies)

        harvested = await CookieHarvester().harvest(browser, URL)

        names = {c["name"] for c in harvested}
        assert names == {"cf_clearance", "session"}
        cf = next(c for c in harvested if c["name"] == "cf_clearance")
        assert "expires" in cf
        session = next(c for c in harvested if c["name"] == "session")
        assert "expires" not in session  # session cookie (expires <= 0) omitted
