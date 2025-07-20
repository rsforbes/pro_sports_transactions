"""Unit tests for date parameter handling."""
from datetime import date

import pytest

from pro_sports_transactions.search import Parameter

testdata = [
    ("correct", date.fromisoformat("2010-12-01"), "2010-12-01"),
    ("none", None, ""),
    ("string", "2010-12-01", ""),
]


@pytest.mark.unit
@pytest.mark.parametrize("key, value, return_value", testdata)
def test_get_date_param(key, value, return_value):
    """Test date parameter generation with various input types."""
    actual = Parameter.date_param(key=key, value=value)
    expected = {key: return_value}
    assert expected == actual
