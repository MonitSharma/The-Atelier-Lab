from trace_policy import trace_directory


def test_trace_directory_matches_project_docs():
    assert trace_directory() == "data/traces"
