from runtime_policy import cloud_apis_allowed


def test_runtime_policy_matches_project_constraints():
    assert cloud_apis_allowed() is False
