from series import double, fibonacci


def test_fibonacci_base_cases():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_fibonacci_later_values():
    assert fibonacci(6) == 8


def test_double():
    assert double(4) == 8
