from pro_sports_transactions.search import League, TransactionType, Parameter
import pytest


def pytest_generate_tests(metafunc):
    if "league" in metafunc.fixturenames and "transaction_type" in metafunc.fixturenames:
        metafunc.parametrize(
            ("league", "transaction_type"),
            [
                (league, transaction_type)
                for league in League
                for transaction_type in TransactionType
            ],
        )


@pytest.fixture()
def league(request):
    return request.param


@pytest.fixture()
def transaction_type(request):
    return request.param


def test_transaction_type_param(league: League, transaction_type: TransactionType):
    actual = Parameter.transaction_type(param_name=transaction_type[league])
    expected = {TransactionType[transaction_type.name][league]: "yes"}
    assert expected == actual
