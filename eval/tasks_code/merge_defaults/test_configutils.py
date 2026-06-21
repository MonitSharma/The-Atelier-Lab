from configutils import has_key, merge_defaults


def test_merge_defaults_returns_combined_copy():
    defaults = {"timeout": 30, "retries": 2}
    merged = merge_defaults(defaults, {"retries": 5})
    assert merged == {"timeout": 30, "retries": 5}
    assert defaults == {"timeout": 30, "retries": 2}


def test_has_key():
    assert has_key({"a": 1}, "a")
