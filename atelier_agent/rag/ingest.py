"""Content-addressed, incremental local ingestion."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atelier.config import settings
from rag.chunk import Chunk, split_markdown, split_plain
from rag.extract import extract_text_sections
from rag.manifest import DocumentRecord, IndexManifest
from rag.paper import chunk_pdf, load_metadata, sha256_file

MARKDOWN_EXT = {".md", ".markdown", ".mdx"}
TEXT_EXT = {".txt", ".rst", ".org", ".adoc", ".html", ".htm", ".rtf", ".tex", ".ipynb", ".log"}
CODE_EXT = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".h",
    ".cpp", ".hpp", ".rb", ".sh", ".sql", ".toml", ".yaml", ".yml", ".json", ".csv", ".tsv",
}
PDF_EXT = {".pdf"}
OFFICE_EXT = {".docx", ".pptx", ".xlsx", ".xlsm"}
BOOK_EXT = {".epub"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
ARCHIVE_EXT = {".zip"}
SUPPORTED = MARKDOWN_EXT | TEXT_EXT | CODE_EXT | PDF_EXT | OFFICE_EXT | BOOK_EXT | IMAGE_EXT | ARCHIVE_EXT
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__",
             ".pytest_cache", ".ruff_cache", "data", "dist", "build"}


@dataclass(frozen=True)
class FilePlan:
    path: Path
    document_id: str
    kind: str
    old_document_id: str | None = None
    size_bytes: int = 0
    mtime_ns: int = 0


@dataclass(frozen=True)
class IngestPlan:
    entries: tuple[FilePlan, ...]
    removed: tuple[DocumentRecord, ...] = ()

    def counts(self) -> dict[str, int]:
        result = {key: 0 for key in ("unchanged", "new", "modified", "relocated", "duplicate", "removed", "forced")}
        for entry in self.entries:
            result[entry.kind] = result.get(entry.kind, 0) + 1
        result["removed"] = len(self.removed)
        return result


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iter_files(root: Path) -> Iterable[Path]:
    """Yield supported files below an explicit root, skipping junk children."""
    root = root.expanduser().resolve()
    if root.is_file():
        if root.suffix.lower() in SUPPORTED:
            yield root
        return
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts[:-1]):
            continue
        if path.suffix.lower() in SUPPORTED:
            yield path


def files_under(paths: Iterable[str | Path]) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for raw in paths:
        root = Path(raw).expanduser().resolve()
        if not root.exists():
            continue
        for path in iter_files(root):
            if path not in seen:
                seen.add(path)
                files.append(path)
    return sorted(files)


def _doc_type(path: Path) -> str:
    if path.suffix.lower() in PDF_EXT:
        return "research_paper"
    if path.suffix.lower() in MARKDOWN_EXT:
        return "markdown"
    if path.suffix.lower() in CODE_EXT:
        return "code"
    if path.suffix.lower() == ".docx":
        return "document"
    if path.suffix.lower() == ".pptx":
        return "presentation"
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return "spreadsheet"
    if path.suffix.lower() in BOOK_EXT:
        return "book"
    if path.suffix.lower() in IMAGE_EXT:
        return "image"
    if path.suffix.lower() in ARCHIVE_EXT:
        return "archive"
    return "text"


def chunk_file(path: Path, *, document_id: str | None = None) -> list[Chunk]:
    """Extract/chunk one file; callers use the manifest to avoid repeated work."""
    path = path.expanduser().resolve()
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        return []
    document_id = document_id or sha256_file(path)
    if ext in PDF_EXT:
        metadata = load_metadata(path, document_id)
        identity = metadata.identity.model_dump() if metadata else {}
        return chunk_pdf(path, document_id=document_id, identity=identity)
    base_meta: dict[str, Any] = {
        "filename": path.name, "ext": ext, "doc_type": _doc_type(path),
        "document_id": document_id, "metadata_schema_version": settings.metadata_schema_version,
    }
    if ext in CODE_EXT:
        base_meta["language"] = ext.lstrip(".")
        text = _read_text(path)
        return split_plain(text, str(path), base_meta=base_meta)
    if ext in MARKDOWN_EXT:
        return split_markdown(_read_text(path), str(path), base_meta=base_meta)
    if ext in OFFICE_EXT | BOOK_EXT | IMAGE_EXT | ARCHIVE_EXT:
        chunks: list[Chunk] = []
        for section_text, section_meta in extract_text_sections(path):
            metadata = {**base_meta, **section_meta}
            pieces = split_plain(section_text, str(path), base_meta=metadata)
            for piece in pieces:
                piece.chunk_index += len(chunks)
                chunks.append(piece)
        return chunks
    return split_plain(_read_text(path), str(path), base_meta=base_meta)


def ingest_paths(paths: Iterable[str | Path]) -> tuple[list[Chunk], list[Path]]:
    """Compatibility helper: eagerly chunk all supported files."""
    chunks: list[Chunk] = []
    files: list[Path] = []
    for path in files_under(paths):
        file_chunks = chunk_file(path)
        if file_chunks:
            chunks.extend(file_chunks)
            files.append(path)
    return chunks, files


def _under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def build_plan(
    paths: Iterable[str | Path],
    manifest: IndexManifest,
    *,
    force: bool = False,
    sync: bool = False,
) -> IngestPlan:
    files = files_under(paths)
    entries: list[FilePlan] = []
    seen_paths = {str(path) for path in files}
    roots = [Path(raw).expanduser().resolve() for raw in paths]
    for path in files:
        document_id = sha256_file(path)
        stat = path.stat()
        by_path = manifest.get_by_path(path)
        by_hash = manifest.get(document_id)
        if force:
            kind = "forced"
        elif by_path and by_path.document_id == document_id:
            kind = "unchanged"
        elif by_hash and (by_path is None or by_path.document_id != document_id):
            hash_path_exists = Path(by_hash.current_path).exists()
            kind = "duplicate" if hash_path_exists else "relocated"
        elif by_path:
            kind = "modified"
        else:
            kind = "new"
        entries.append(FilePlan(path, document_id, kind,
                                by_path.document_id if by_path and by_path.document_id != document_id else None,
                                stat.st_size, stat.st_mtime_ns))

    removed: list[DocumentRecord] = []
    if sync:
        for record in manifest.all():
            if any(_under_root(Path(record.current_path), root) for root in roots):
                if record.current_path not in seen_paths:
                    removed.append(record)
    return IngestPlan(tuple(entries), tuple(removed))


def bootstrap_manifest_from_store(
    manifest: IndexManifest, store: Any, paths: Iterable[str | Path]
) -> int:
    """Register an existing compatible Chroma index without re-extracting it."""
    if manifest.all() or store.count() == 0:
        return 0
    allowed = {str(path.resolve()) for path in files_under(paths)}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for metadata in store.get_all().get("metadatas", []):
        document_id = metadata.get("document_id")
        source = str(Path(metadata.get("source", "")).resolve())
        if document_id and source in allowed:
            grouped.setdefault(document_id, []).append(metadata)
    registered = 0
    for document_id, metadatas in grouped.items():
        source = Path(metadatas[0]["source"]).resolve()
        if not source.exists() or sha256_file(source) != document_id:
            continue
        stat = source.stat()
        manifest.upsert_document(
            document_id=document_id, path=source, size_bytes=stat.st_size,
            mtime_ns=stat.st_mtime_ns, chunk_count=len(metadatas),
            doc_type=metadatas[0].get("doc_type", _doc_type(source)),
        )
        registered += 1
    dimension = store.embedding_dimension()
    if registered:
        manifest.set_state(
            embedding_model=settings.embed_model if dimension == settings.embed_dimension else "unknown",
            embedding_dimension=dimension or "unknown",
            index_schema_version=settings.index_schema_version,
            chunk_schema_version=settings.chunk_schema_version,
        )
    return registered


def _register_state(manifest: IndexManifest, embedder: Any, chunk_count: int) -> None:
    manifest.set_state(
        embedding_model=getattr(embedder, "model_name", settings.embed_model),
        embedding_dimension=getattr(embedder, "dim", 0),
        index_schema_version=settings.index_schema_version,
        chunk_schema_version=settings.chunk_schema_version,
        last_chunk_count=chunk_count,
    )


def execute_plan(
    plan: IngestPlan,
    manifest: IndexManifest,
    store: Any,
    embedder: Any,
    *,
    dry_run: bool = False,
) -> dict[str, int]:
    """Apply a plan; modified records are replaced only after new vectors exist."""
    counts = plan.counts()
    if dry_run:
        return counts

    for record in plan.removed:
        store.delete_document(record.document_id)
        manifest.remove(record.document_id)

    changed = [entry for entry in plan.entries if entry.kind in {"new", "modified", "forced"}]
    for entry in changed:
        chunks = chunk_file(entry.path, document_id=entry.document_id)
        vectors = embedder.embed_passages([chunk.text for chunk in chunks]) if chunks else []
        if not entry.old_document_id and hasattr(store, "replace_document"):
            store.replace_document(entry.document_id, chunks, vectors)
        else:
            store.add(chunks, vectors)
        if entry.old_document_id:
            store.delete_document(entry.old_document_id)
            manifest.remove(entry.old_document_id)
        manifest.upsert_document(
            document_id=entry.document_id, path=entry.path, size_bytes=entry.size_bytes,
            mtime_ns=entry.mtime_ns, chunk_count=len(chunks), doc_type=_doc_type(entry.path),
        )

    for entry in plan.entries:
        if entry.kind == "relocated":
            store.relocate_document(entry.document_id, str(entry.path.resolve()))
            record = manifest.get(entry.document_id)
            if record:
                manifest.upsert_document(
                    document_id=entry.document_id, path=entry.path, size_bytes=entry.size_bytes,
                    mtime_ns=entry.mtime_ns, chunk_count=record.chunk_count, doc_type=record.doc_type,
                )
        elif entry.kind == "duplicate":
            manifest.add_alias(entry.document_id, entry.path)
            if entry.old_document_id:
                store.delete_document(entry.old_document_id)
                manifest.remove(entry.old_document_id)

    if changed:
        _register_state(manifest, embedder, sum(
            manifest.get(entry.document_id).chunk_count for entry in changed
            if manifest.get(entry.document_id)
        ))
    return counts
