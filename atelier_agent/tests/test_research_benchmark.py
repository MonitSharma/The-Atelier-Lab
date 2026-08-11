from eval.research_benchmark import load_suite


def test_research_benchmark_suite_is_frozen_and_has_expected_shape():
    suite = load_suite()

    assert suite["suite"] == "research_deep_v1"
    assert len(suite["cases"]) >= 8
    assert all(case.get("id") and case.get("question") for case in suite["cases"])
