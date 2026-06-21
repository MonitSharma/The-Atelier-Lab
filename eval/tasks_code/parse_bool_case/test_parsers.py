import pytest

from parsers import parse_bool, parse_int


def test_parse_bool_accepts_case_and_spaces:
    assert parse_bool(" TRUE ") is True
    assert parse_bool("False") is False


def test_parse_bool_rejects_unknown_values():
    with pytest.raises(ValueError):
        parse_bool("yes")


def test_parse_int():
    assert parse_int(" 42 ") == 42
