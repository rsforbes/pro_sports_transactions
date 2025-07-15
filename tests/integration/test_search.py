from datetime import date, timedelta
from pro_sports_transactions.search import Search, League, TransactionType
import pytest
import json


@pytest.mark.asyncio
async def test_search_basic_functionality():
    """Test that Search class returns proper structure with recent data"""
    # Use recent dates that should have some transactions
    end_date = date.today()
    start_date = end_date - timedelta(days=30)  # Last 30 days

    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=start_date,
        end_date=end_date,
    )

    result = await search.get_dict()

    # Verify structure regardless of data content
    assert "transactions" in result
    assert "pages" in result
    assert isinstance(result["transactions"], list)
    assert isinstance(result["pages"], int)
    assert result["pages"] >= 0

    # If there are transactions, verify their structure
    if result["transactions"]:
        transaction = result["transactions"][0]
        required_keys = ["Date", "Team", "Acquired", "Relinquished", "Notes"]
        for key in required_keys:
            assert key in transaction
            assert isinstance(transaction[key], str)


@pytest.mark.asyncio
async def test_search_json_format():
    """Test that get_json returns valid JSON"""
    # Use a simple recent search
    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=date.today() - timedelta(days=7),
        end_date=date.today(),
    )

    json_result = await search.get_json()

    # Should be valid JSON
    parsed = json.loads(json_result)
    assert isinstance(parsed, dict)
    assert "transactions" in parsed
    assert "pages" in parsed


@pytest.mark.asyncio
async def test_search_url_generation():
    """Test that URL generation works correctly"""
    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement, TransactionType.InjuredList),
        start_date=date.fromisoformat("2023-01-01"),
        end_date=date.fromisoformat("2023-01-31"),
        player="Test Player",
        team="Test Team",
    )

    url = await search.get_url()

    # Verify URL components
    assert "prosportstransactions.com" in url
    assert "basketball" in url  # NBA league
    assert "PlayerMovementChkBx=yes" in url
    assert "ILChkBx=yes" in url
    assert "Player=Test+Player" in url or "Player=Test%20Player" in url
    assert "Team=Test+Team" in url or "Team=Test%20Team" in url
    assert "BeginDate=2023-01-01" in url
    assert "EndDate=2023-01-31" in url


@pytest.mark.asyncio
async def test_search_with_specific_player():
    """Test search with a specific player using recent data"""
    # Use a common player name and recent timeframe
    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement, TransactionType.InjuredList),
        start_date=date.fromisoformat("2023-01-01"),
        end_date=date.fromisoformat("2023-12-31"),
        player="James",  # Common surname, should find some results
    )

    result = await search.get_dict()

    # Verify structure
    assert "transactions" in result
    assert "pages" in result

    # Either we get results or empty results (both are valid)
    assert isinstance(result["transactions"], list)
    assert isinstance(result["pages"], int)


@pytest.mark.asyncio
async def test_search_error_handling():
    """Test that search handles errors gracefully"""
    # Use invalid date range that might cause issues
    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=date.fromisoformat("1800-01-01"),  # Very old date
        end_date=date.fromisoformat("1800-01-31"),
    )

    result = await search.get_dict()

    # Should not crash, should return proper structure
    assert "transactions" in result
    assert "pages" in result
    assert isinstance(result["transactions"], list)
    assert isinstance(result["pages"], int)

    # May have errors in result, which is acceptable
    if "errors" in result:
        assert isinstance(result["errors"], (list, tuple))


@pytest.mark.asyncio
async def test_search_multiple_leagues():
    """Test searches across different leagues"""
    leagues_to_test = [League.NBA, League.NFL, League.MLB]

    for league in leagues_to_test:
        search = Search(
            league=league,
            transaction_types=(TransactionType.Movement,),
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
        )

        result = await search.get_dict()

        # Each league should return proper structure
        assert "transactions" in result
        assert "pages" in result
        assert isinstance(result["transactions"], list)
        assert isinstance(result["pages"], int)

        # URL should contain the correct league
        url = await search.get_url()
        assert league.value in url  # e.g., "basketball", "football", "baseball"


@pytest.mark.asyncio
async def test_search_unicode_handling():
    """Test that unicode characters in player names are handled properly"""
    # Test with unicode characters (like O'Neal)
    search = Search(
        league=League.NBA,
        transaction_types=(TransactionType.Movement,),
        start_date=date.fromisoformat("2020-01-01"),
        end_date=date.fromisoformat("2023-12-31"),
        player="O'Neal",  # Has apostrophe
    )

    # Should not crash with unicode characters
    result = await search.get_dict()
    assert "transactions" in result
    assert "pages" in result

    # URL should properly encode unicode
    url = await search.get_url()
    assert "Player=" in url
    # Should be URL encoded
    assert "O%27Neal" in url or "O'Neal" in url
