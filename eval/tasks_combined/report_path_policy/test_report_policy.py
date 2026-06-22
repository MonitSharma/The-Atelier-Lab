from report_policy import eval_report_directory


def test_eval_report_directory_matches_project_docs():
    assert eval_report_directory() == "data/eval_reports"
