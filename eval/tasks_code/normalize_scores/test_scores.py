from scores import best, normalize


def test_normalize_min_max_scales_values():
    assert normalize([10, 20, 30]) == [0.0, 0.5, 1.0]


def test_normalize_constant_scores_are_zero():
    assert normalize([5, 5, 5]) == [0.0, 0.0, 0.0]


def test_best():
    assert best([10, 20, 30]) == 30
