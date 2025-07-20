"""Unit tests for URL building functionality."""
from datetime import date
from urllib import parse

import pytest

from pro_sports_transactions.search import League, TransactionType, UrlBuilder


def pytest_generate_tests(metafunc):
    """Generate test parameters for all leagues."""
    if "league_param" in metafunc.fixturenames:
        metafunc.parametrize(
            ("league_param"),
            list(League),
        )


@pytest.fixture(name="league_param")
def league(request):
    """Fixture providing league parameter."""
    return request.param


@pytest.mark.unit
def test_build_url(league_param: League):
    """Test URL building for league-specific transaction searches."""
    transaction_types = tuple(TransactionType)
    start_date = date.fromisoformat("2000-01-05")
    end_date = date.fromisoformat("2006-04-05")

    actual = parse.urlparse(
        url=UrlBuilder.build(
            league=league_param,
            transaction_types=transaction_types,
            start_date=start_date,
            end_date=end_date,
            player="O'Neal",
            team="Pacers",
            starting_row=25,
        )
    )

    transaction_type_param = ""
    for transaction_type in TransactionType:
        transaction_type_param += (
            f"{TransactionType[transaction_type.name][league_param]}=yes&"
        )

    expected = parse.urlparse(
        f"https://www.prosportstransactions.com/{league_param.value}/Search"
        "/SearchResults.php?Player=O%27Neal&Team=Pacers&BeginDate=2000-01-05"
        f"&EndDate=2006-04-05&{transaction_type_param}"
        "&Submit=Search&start=25"
    )

    assert expected.scheme == actual.scheme
    assert expected.netloc == actual.netloc
    assert expected.path == actual.path
    assert parse.parse_qs(actual.query) == parse.parse_qs(expected.query)
