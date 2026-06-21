from numberutils import clamp, percent


def test_clamp_inside_range():
    assert clamp(5, 0, 10) == 5


def test_clamp_outside_range():
    assert clamp(-3, 0, 10) == 0
    assert clamp(12, 0, 10) == 10


def test_percent():
    assert percent(2, 8) == 25
