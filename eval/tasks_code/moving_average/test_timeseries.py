from timeseries import latest, moving_average


def test_moving_average_includes_final_window():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]
    assert moving_average([10, 20, 30], 3) == [20]


def test_latest():
    assert latest([1, 2, 3]) == 3
