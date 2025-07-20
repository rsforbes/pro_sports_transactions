"""Integration tests for search functionality."""
# pylint: disable=duplicate-code  # Test files naturally have similar test data
from datetime import date

import pytest

import pro_sports_transactions as pst
from pro_sports_transactions.search import League, Search, TransactionType


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_unicode():
    """
    Test direct Search calls (expected to fail due to Cloudflare JA4 protection).
    This test documents the current state where direct calls are blocked.
    Use UnflareRequestHandler for working requests.
    """
    transaction_types = tuple(TransactionType)
    start_date = date.fromisoformat("2000-01-05")
    end_date = date.fromisoformat("2005-04-05")

    actual = await Search(
        league=League.NBA,
        transaction_types=transaction_types,
        start_date=start_date,
        end_date=end_date,
        player="O'Neal",
        team="Pacers",
        starting_row=25,
    ).get_json()

    # Expected failure due to Cloudflare JA4 protection blocking direct requests
    expected_cloudflare_blocked = (
        '{"transactions": [], "pages": 0, '
        '"errors": ["TypeError(\\"cannot parse from \'NoneType\'\\")"]}'
    )

    assert actual == expected_cloudflare_blocked


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_readme_md_example():
    """
    Test README example with direct Search calls (expected to fail due to
    Cloudflare JA4 protection).
    This test documents the current state where direct calls are blocked.
    Use UnflareRequestHandler for working requests.
    """
    # League (MLB, MLS, NBA, NFL, and NHL)
    league = pst.League.NBA

    # Disciplinary Actions, Injured List, Injuries,
    # Legal Incidents, Minor League To/For, Personal Reasons,
    # and General (e.g., Trades, Acquisitions, Waivers, Draft Picks, etc.)
    transaction_types = tuple(pst.TransactionType)

    # From the start of the 2022-23 NBA Regular Season
    start_date = date.fromisoformat("2022-10-18")

    # From the end of the 2022-23 NBA Regular Season
    end_date = date.fromisoformat("2023-04-09")

    # Pro Sports Transactions provides 25 rows (one page) at a time.
    # The first row of the first page is always 0, and ends with 24.
    # The first row of the second page is always 25, and ends with 49.
    # Note: If the starting_row is set to 9; the 10th row of the results,
    # then the last row of the first page wil be 34 (9 + 25)..
    starting_row = 0

    # How to Search
    actual = await pst.Search(
        league=league,
        transaction_types=transaction_types,
        start_date=start_date,
        end_date=end_date,
        player="LeBron James",
        team="Lakers",
        starting_row=starting_row,
    ).get_json()

    # Expected failure due to Cloudflare JA4 protection blocking direct requests
    expected_cloudflare_blocked = (
        '{"transactions": [], "pages": 0, '
        '"errors": ["TypeError(\\"cannot parse from \'NoneType\'\\")"]}'
    )

    assert actual == expected_cloudflare_blocked
