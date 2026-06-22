from embedding_policy import default_embedding_model


def test_embedding_model_matches_project_docs():
    assert default_embedding_model() == "BAAI/bge-base-en-v1.5"
