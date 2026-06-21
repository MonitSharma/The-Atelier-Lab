from project_prefs import preferred_test_framework


def test_project_uses_user_preferred_test_framework():
    assert preferred_test_framework() == "pytest"
