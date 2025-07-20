"""Unit tests for transaction type parameter handling."""
import pytest

from pro_sports_transactions.search import League, Parameter, TransactionType


def pytest_generate_tests(metafunc):
    """Generate test parameters for league and transaction type combinations."""
    if (
        "league_param" in metafunc.fixturenames and
        "transaction_type_param" in metafunc.fixturenames
    ):
        metafunc.parametrize(
            ("league_param", "transaction_type_param"),
            [
                (league, transaction_type)
                for league in League
                for transaction_type in TransactionType
            ],
        )


@pytest.fixture(name="league_param")
def league(request):
    """Fixture providing league parameter."""
    return request.param


@pytest.fixture(name="transaction_type_param")
def transaction_type(request):
    """Fixture providing transaction type parameter."""
    return request.param


@pytest.mark.unit
def test_transaction_type_param(
    league_param: League, transaction_type_param: TransactionType
):
    """Test transaction type parameter generation for league-specific forms."""
    actual = Parameter.transaction_type(param_name=transaction_type_param[league_param])
    expected = {TransactionType[transaction_type_param.name][league_param]: "yes"}
    assert expected == actual
