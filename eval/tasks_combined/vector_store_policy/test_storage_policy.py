from storage_policy import vector_store_name


def test_vector_store_matches_project_docs():
    assert vector_store_name() == "ChromaDB"
