from service import search


def test_search_is_case_insensitive_and_does_not_mutate_input():
    rows = [{"title": "Quantum Routing"}, {"title": "Classical Search"}]
    original = list(rows)
    assert search(rows, "QUANTUM") == [rows[0]]
    assert rows == original


def test_search_limit_is_applied_after_matching():
    rows = [{"title": "a quantum"}, {"title": "b quantum"}, {"title": "other"}]
    assert search(rows, "quantum", limit=1) == [rows[0]]
