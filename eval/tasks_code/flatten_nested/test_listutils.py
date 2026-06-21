from listutils import flatten, head


def test_flatten_expands_one_level():
    assert flatten([[1, 2], [3], [], [4, 5]]) == [1, 2, 3, 4, 5]


def test_flatten_preserves_scalar_items():
    assert flatten([1, [2, 3], 4]) == [1, 2, 3, 4]


def test_head():
    assert head(["a", "b"]) == "a"
