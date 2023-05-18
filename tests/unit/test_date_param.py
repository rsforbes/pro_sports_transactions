from datetime import date
from pro_sports_transactions.search import Parameter
import pytest

testdata = [
    ("correct", date.fromisoformat("2010-12-01"), "2010-12-01"),
    ("none", None, ""),
    ("string", "2010-12-01", ""),
]


@pytest.mark.parametrize("key, value, return_value", testdata)
def test_get_date_param(key, value, return_value):
    actual = Parameter.date_param(key=key, value=value)
    expected = {key: return_value}
    assert expected == actual
