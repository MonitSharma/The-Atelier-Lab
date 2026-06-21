from listutils import first_n, last


def test_first_n():
    assert first_n([1, 2, 3, 4], 2) == [1, 2]
    assert first_n([9, 8, 7], 3) == [9, 8, 7]


def test_last():
    assert last([1, 2, 3]) == 3
