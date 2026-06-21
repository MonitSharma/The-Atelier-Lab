from collections_utils import count_items, unique


def test_unique_preserves_first_seen_order():
    assert unique(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_count_items():
    assert count_items([1, 2, 3]) == 3
