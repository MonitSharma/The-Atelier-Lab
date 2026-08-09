from records import normalize_records, passing_records
from report import summarize


def test_normalization_and_inclusive_threshold():
    rows = normalize_records([{"name": " Alice ", "score": 0.5}, {"name": "Bob", "score": 0.8}])
    assert rows[0]["name"] == "Alice"
    assert passing_records(rows) == rows


def test_summary_handles_empty_records():
    assert summarize([]) == {"count": 0, "passing": 0, "average": 0.0}


def test_summary_uses_normalized_rows():
    assert summarize([{"name": " A ", "score": 0.2}, {"name": "B", "score": 0.8}]) == {
        "count": 2, "passing": 1, "average": 0.5
    }
