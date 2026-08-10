
from rag.ingest import build_plan, execute_plan
from rag.manifest import IndexManifest


class CountingEmbedder:
    model_name = "test-embedder"
    dim = 3

    def __init__(self):
        self.calls = []

    def embed_passages(self, texts):
        self.calls.append(list(texts))
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeStore:
    def __init__(self):
        self.docs = {}

    def add(self, chunks, embeddings):
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self.docs[(chunk.metadata["document_id"], chunk.chunk_index)] = (chunk, embedding)
        return len(chunks)

    def replace_document(self, document_id, chunks, embeddings):
        self.delete_document(document_id)
        return self.add(chunks, embeddings)

    def delete_document(self, document_id):
        old = [key for key in self.docs if key[0] == document_id]
        for key in old:
            del self.docs[key]
        return len(old)

    def relocate_document(self, document_id, source):
        for chunk, _embedding in self.docs.values():
            if chunk.metadata["document_id"] == document_id:
                chunk.source = source
        return 1


def test_incremental_new_unchanged_rename_modify_and_sync(tmp_path):
    manifest = IndexManifest(tmp_path / "manifest.sqlite3")
    store = FakeStore()
    embedder = CountingEmbedder()
    path = tmp_path / "paper.txt"
    path.write_text("first content", encoding="utf-8")

    first = build_plan([tmp_path], manifest)
    assert first.counts()["new"] == 1
    execute_plan(first, manifest, store, embedder)
    assert len(embedder.calls) == 1
    original_id = manifest.all()[0].document_id

    second = build_plan([tmp_path], manifest)
    assert second.counts()["unchanged"] == 1
    execute_plan(second, manifest, store, embedder)
    assert len(embedder.calls) == 1

    renamed = tmp_path / "renamed.txt"
    path.rename(renamed)
    relocated = build_plan([tmp_path], manifest)
    assert relocated.counts()["relocated"] == 1
    execute_plan(relocated, manifest, store, embedder)
    assert len(embedder.calls) == 1
    assert manifest.all()[0].document_id == original_id
    assert manifest.all()[0].current_path == str(renamed.resolve())

    renamed.write_text("changed content", encoding="utf-8")
    modified = build_plan([tmp_path], manifest)
    assert modified.counts()["modified"] == 1
    execute_plan(modified, manifest, store, embedder)
    assert len(embedder.calls) == 2
    assert manifest.all()[0].document_id != original_id

    duplicate = tmp_path / "copy.txt"
    duplicate.write_text("changed content", encoding="utf-8")
    duplicate_plan = build_plan([duplicate], manifest)
    assert duplicate_plan.counts()["duplicate"] == 1
    execute_plan(duplicate_plan, manifest, store, embedder)
    assert len(embedder.calls) == 2

    duplicate.unlink()
    no_sync = build_plan([tmp_path], manifest)
    assert not no_sync.removed
    sync = build_plan([tmp_path], manifest, sync=True)
    assert sync.counts()["removed"] == 0  # current path still exists
    renamed.unlink()
    ordinary = build_plan([tmp_path], manifest)
    assert not ordinary.removed
    reconciled = build_plan([tmp_path], manifest, sync=True)
    assert reconciled.counts()["removed"] == 1


def test_dry_run_does_not_embed(tmp_path):
    manifest = IndexManifest(tmp_path / "manifest.sqlite3")
    store = FakeStore()
    embedder = CountingEmbedder()
    path = tmp_path / "note.md"
    path.write_text("hello", encoding="utf-8")
    plan = build_plan([path], manifest)
    before = manifest.all()
    execute_plan(plan, manifest, store, embedder, dry_run=True)
    assert not embedder.calls
    assert manifest.all() == before


def test_multiple_files_share_one_embedding_batch(tmp_path):
    manifest = IndexManifest(tmp_path / "manifest.sqlite3")
    store = FakeStore()
    embedder = CountingEmbedder()
    (tmp_path / "first.txt").write_text("first content", encoding="utf-8")
    (tmp_path / "second.txt").write_text("second content", encoding="utf-8")

    plan = build_plan([tmp_path], manifest)
    execute_plan(plan, manifest, store, embedder)

    assert len(embedder.calls) == 1
    assert len(embedder.calls[0]) == 2
    assert len(store.docs) == 2
