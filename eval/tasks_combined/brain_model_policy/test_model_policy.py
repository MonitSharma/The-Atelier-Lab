from model_policy import default_brain_model


def test_default_brain_model_matches_project_docs():
    assert default_brain_model() == "qwen3:14b"
