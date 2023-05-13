from datetime import date
from pro_sports_transactions.search import Parameter


def test_get_date_param():
    test_parameter = "test_param"
    test_date = date.fromisoformat("2010-12-01")
    iso8601 = test_date.strftime("%Y-%m-%d")

    actual = Parameter.date_param(key=test_parameter, value=test_date)
    expected = {test_parameter: iso8601}
    assert expected == actual
