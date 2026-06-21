"""Load files from disk into chunks ready for embedding.

Supported out of the box: Markdown, plain text, PDF, and common source-code
files. Ingestion is a *user-driven, offline* step (unlike the agent's sandboxed
file tool), so it may read from anywhere you point it — your real notes folder,
an Obsidian vault, a papers directory — nothing leaves the machine.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from rag.chunk import Chunk, split_markdown, split_plain

MARKDOWN_EXT = {".md", ".markdown", ".mdx"}
TEXT_EXT = {".txt", ".rst", ".org"}
CODE_EXT = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".h",
    ".cpp", ".hpp", ".rb", ".sh", ".sql", ".toml", ".yaml", ".yml", ".json",
}
PDF_EXT = {".pdf"}
SUPPORTED = MARKDOWN_EXT | TEXT_EXT | CODE_EXT | PDF_EXT

# Directories we never descend into.
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__",
             ".pytest_cache", ".ruff_cache", "data", "dist", "build"}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    import fitz  # pymupdf

    parts: list[str] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                parts.append(f"[page {i}]\n{text}")
    return "\n\n".join(parts)


def chunk_file(path: Path) -> list[Chunk]:
    """Load one file and return its chunks, or [] if unsupported/empty."""
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        return []
    source = str(path.resolve())
    base_meta = {"filename": path.name, "ext": ext}

    if ext in PDF_EXT:
        text = _read_pdf(path)
        base_meta["doc_type"] = "pdf"
        return split_plain(text, source, base_meta=base_meta)
    if ext in MARKDOWN_EXT:
        base_meta["doc_type"] = "markdown"
        return split_markdown(_read_text(path), source, base_meta=base_meta)
    if ext in CODE_EXT:
        base_meta["doc_type"] = "code"
        base_meta["language"] = ext.lstrip(".")
        return split_plain(_read_text(path), source, base_meta=base_meta)
    base_meta["doc_type"] = "text"
    return split_plain(_read_text(path), source, base_meta=base_meta)


def iter_files(root: Path) -> Iterable[Path]:
    """Yield supported files under ``root`` (recursively), skipping junk dirs."""
    if root.is_file():
        yield root
        return
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in SUPPORTED:
            yield p


def ingest_paths(paths: Iterable[str | Path]) -> tuple[list[Chunk], list[Path]]:
    """Chunk every supported file found under the given paths.

    Returns ``(chunks, files_seen)`` so callers can report what was indexed.
    """
    chunks: list[Chunk] = []
    files: list[Path] = []
    for raw in paths:
        root = Path(raw).expanduser().resolve()
        if not root.exists():
            continue
        for f in iter_files(root):
            file_chunks = chunk_file(f)
            if file_chunks:
                chunks.extend(file_chunks)
                files.append(f)
    return chunks, files
