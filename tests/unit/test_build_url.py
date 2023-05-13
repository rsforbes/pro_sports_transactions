from datetime import date
from pro_sports_transactions.search import League, TransactionTypes, UrlBuilder
from urllib import parse
import pytest


def pytest_generate_tests(metafunc):
    if "league" in metafunc.fixturenames:
        metafunc.parametrize(
            ("league"),
            [(league) for league in League],
        )


@pytest.fixture()
def league(request):
    return request.param


def test_build_url(league: League):
    transaction_types = tuple([t for t in TransactionTypes])
    start_date = date.fromisoformat("2000-01-05")
    end_date = date.fromisoformat("2006-04-05")

    actual = parse.urlparse(
        url=UrlBuilder.build(
            league=league,
            transaction_types=transaction_types,
            start_date=start_date,
            end_date=end_date,
            player="O'Neal",
            team="Pacers",
            starting_row=25,
        )
    )

    transaction_type_param = ""
    for transaction_type in TransactionTypes:
        transaction_type_param += f"{TransactionTypes[transaction_type.name][league]}=yes&"

    expected = parse.urlparse(
        f"https://www.prosportstransactions.com/{league.value}/Search"
        "/SearchResults.php?Player=O%27Neal&Team=Pacers&BeginDate=2000-01-05"
        f"&EndDate=2006-04-05&{transaction_type_param}"
        "&Submit=Search&start=25"
    )

    assert expected.scheme == actual.scheme
    assert expected.netloc == actual.netloc
    assert expected.path == actual.path
    assert parse.parse_qs(actual.query) == parse.parse_qs(expected.query)
