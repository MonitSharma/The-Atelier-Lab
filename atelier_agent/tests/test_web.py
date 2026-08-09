from atelier.web import render_index


def test_web_workbench_contains_core_panels_and_local_api_calls():
    page = render_index()
    for label in ("Workspace & privacy", "Models", "Library", "Workflows", "Recent traces", "Approvals"):
        assert label in page
    assert "fetch('/route'" in page
    assert "fetch('/search'" in page
    assert "fetch('/workflow_approve'" in page
