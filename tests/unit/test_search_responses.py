"""Unit tests for search response handling."""

from pathlib import Path

import pytest

import pro_sports_transactions as pst
from pro_sports_transactions.handlers import RequestHandler
from pro_sports_transactions.search import TransactionType

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def create_mock_coro(mocker, monkeypatch):
    """Create a mock-coro pair.

    The coro can be used to patch an async method while the mock can
    be used to assert calls to the mocked out method.
    """

    def _create_mock_coro_pair(to_patch=None):
        mock = mocker.Mock()

        async def _coro(*args, **kwargs):
            return mock(*args, **kwargs)

        if to_patch:
            monkeypatch.setattr(to_patch, _coro)

        return mock, _coro

    return _create_mock_coro_pair


@pytest.fixture(name="valid_response_mock")
def mock_valid_reponse(create_mock_coro):
    """Mock fixture for valid search response."""
    response = None
    # read https://www.prosportstransactions.com/ search results
    with open(
        DATA_DIR / "valid_response.html",
        mode="r",
        encoding="utf-8",
    ) as f:
        response = f.read()

    mock, _ = create_mock_coro(to_patch="pro_sports_transactions.search.Http.get")
    mock.return_value = response

    return mock


@pytest.fixture(name="empty_response_mock")
def mock_empty_reponse(create_mock_coro):
    """Mock fixture for empty search response."""
    response = None
    # read https://www.prosportstransactions.com/ search results
    with open(
        DATA_DIR / "empty_response.html",
        mode="r",
        encoding="utf-8",
    ) as f:
        response = f.read()

    mock, _ = create_mock_coro(to_patch="pro_sports_transactions.search.Http.get")
    mock.return_value = response

    return mock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_valid_response(valid_response_mock):
    """Test parsing valid search response."""
    expected = "".join(
        (
            '{"transactions": [{"Date": "2023-02-15", "Team": "Lakers", ',
            '"Acquired": "\\u2022 LeBron James", "Relinquished": "", "Notes": ',
            '"activated from IL"}, {"Date": "2023-02-27", "Team": "Lakers", ',
            '"Acquired": "", "Relinquished": "\\u2022 LeBron James", "Notes": ',
            '"placed on IL with right foot injury"}, {"Date": "2023-03-26", ',
            '"Team": "Lakers", "Acquired": "\\u2022 LeBron James", ',
            '"Relinquished": "", "Notes": "activated from IL"}], "pages": 1}',
        )
    )

    transaction_types = tuple(TransactionType)

    actual = await pst.Search(
        league=pst.League.NBA,
        transaction_types=transaction_types,
    ).get_json()

    assert expected == actual


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_response(empty_response_mock):
    """Test parsing empty search response."""
    transaction_types = tuple(TransactionType)

    actual = await pst.Search(
        league=pst.League.NBA,
        transaction_types=transaction_types,
    ).get_json()

    expected = (
        '{"transactions": [], "pages": 0, '
        '"errors": ["ValueError(\'No tables found\')"]}'
    )

    assert expected == actual


class _StubHandler(RequestHandler):
    """A request handler that returns a fixed response."""

    def __init__(self, response):
        self.response = response

    async def get(self, url, headers):
        return self.response


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, "", "  \n"], ids=["none", "empty", "blank"])
async def test_no_response_from_handler_reports_error(response):
    """A handler that couldn't fetch the page (e.g. Cloudflare not cleared)
    returns None. Search must report that via errors, not raise (#44)."""
    search = pst.Search(
        league=pst.League.NBA,
        transaction_types=(TransactionType.Movement,),
        request_handler=_StubHandler(response),
    )

    df = await search.get_dataframe()

    assert df.empty
    assert list(df.columns) == ["Date", "Team", "Acquired", "Relinquished", "Notes"]
    assert df.attrs["pages"] == 0
    assert df.attrs["errors"] == ("ValueError('No response from the request handler')",)
    assert (await search.get_dict())["errors"] == df.attrs["errors"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_response_from_default_handler_reports_error(create_mock_coro):
    """The default (Http.get) path returns None when direct requests are
    blocked by Cloudflare. Search must report that via errors, not raise (#44)."""
    mock, _ = create_mock_coro(to_patch="pro_sports_transactions.search.Http.get")
    mock.return_value = None

    df = await pst.Search(
        league=pst.League.NBA, transaction_types=(TransactionType.Movement,)
    ).get_dataframe()

    assert df.empty
    assert df.attrs["errors"] == ("ValueError('No response from the request handler')",)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response", ["<!-- -->", '<?xml version="1.0"?>'], ids=["comment", "xml-decl"]
)
async def test_unparseable_response_reports_error(response):
    """A non-empty document with no parseable text makes lxml raise
    XMLSyntaxError; Search must report it via errors, not raise."""
    df = await pst.Search(
        league=pst.League.NBA,
        transaction_types=(TransactionType.Movement,),
        request_handler=_StubHandler(response),
    ).get_dataframe()

    assert df.empty
    assert df.attrs["pages"] == 0
    assert df.attrs["errors"][0].startswith("XMLSyntaxError(")
