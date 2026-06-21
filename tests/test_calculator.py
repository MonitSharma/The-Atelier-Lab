"""The calculator must evaluate arithmetic and reject anything else.

This replaces the old root-level `unsafe_fail.py` scratch script: it pins the
security property as an actual regression test instead of a manual demo.
"""

import pytest

from tools.calculator import CalculatorError, calculate


def test_basic_arithmetic() -> None:
    assert calculate("2 + 2") == 4
    assert calculate("(3817 * 94) - 628") == 358170
    assert calculate("2 ** 10") == 1024


@pytest.mark.parametrize(
    "expr",
    [
        '__import__("os").system("echo unsafe")',
        "open('/etc/passwd').read()",
        "x + 1",            # names are not allowed
        "1; 2",             # not a single expression
        "[1, 2, 3]",        # not arithmetic
    ],
)
def test_rejects_non_arithmetic(expr: str) -> None:
    with pytest.raises(CalculatorError):
        calculate(expr)


def test_rejects_division_by_zero() -> None:
    with pytest.raises(CalculatorError):
        calculate("1 / 0")
