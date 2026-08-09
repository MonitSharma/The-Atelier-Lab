import pytest

from rag.compat import IndexCompatibilityError, ensure_compatible
from rag.manifest import IndexManifest


class FakeStore:
    def count(self):
        return 1

    def embedding_dimension(self):
        return 768


class FakeEmbedder:
    model_name = "qwen3-embedding:4b"
    dim = 2560


def test_incompatible_index_is_rejected_before_query(tmp_path):
    manifest = IndexManifest(tmp_path / "manifest.sqlite3")
    manifest.set_state(embedding_model="BAAI/bge-base-en-v1.5", embedding_dimension=768)
    with pytest.raises(IndexCompatibilityError, match="Rebuild with"):
        ensure_compatible(FakeStore(), manifest, FakeEmbedder())
