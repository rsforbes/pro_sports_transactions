"""Unit tests for search response handling."""
import pytest

import pro_sports_transactions as pst
from pro_sports_transactions.search import TransactionType


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
def mock_valid_reponse(create_mock_coro):  # pylint: disable=redefined-outer-name
    """Mock fixture for valid search response."""
    response = None
    # read https://www.prosportstransactions.com/ search results
    with open(
        r"/workspaces/pro_sports_transactions/tests/unit/data/valid_response.html",
        mode="r",
        encoding="utf-8",
    ) as f:
        response = f.read()

    mock, _ = create_mock_coro(to_patch="pro_sports_transactions.search.Http.get")
    mock.return_value = response

    return mock


@pytest.fixture(name="empty_response_mock")
def mock_empty_reponse(create_mock_coro):  # pylint: disable=redefined-outer-name
    """Mock fixture for empty search response."""
    response = None
    # read https://www.prosportstransactions.com/ search results
    with open(
        r"/workspaces/pro_sports_transactions/tests/unit/data/empty_response.html",
        mode="r",
        encoding="utf-8",
    ) as f:
        response = f.read()

    mock, _ = create_mock_coro(to_patch="pro_sports_transactions.search.Http.get")
    mock.return_value = response

    return mock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_valid_response(valid_response_mock):  # pylint: disable=unused-argument
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
async def test_empty_response(empty_response_mock):  # pylint: disable=unused-argument
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
