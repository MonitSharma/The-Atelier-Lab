"""Scientific-paper ingestion and fast characterization.

This is the canonical home for the validated Atelier Workbench PDF path. It
uses PyMuPDF4LLM for page-aware Markdown extraction, SHA-256 for stable paper
identity, and the configured worker model for a bounded structured paper card.
The normal ingestion path never calls the model; characterization is explicit.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from atelier.config import settings
from rag.chunk import Chunk, split_plain

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
MAX_CHARACTERIZATION_CHARS = 18_000

CHARACTERIZATION_FIELDS = (
    "title", "paper_type", "domain", "subfields", "research_problem",
    "method", "main_claim", "theoretical", "experimental", "ai_relevance",
    "quantum_relevance", "optimization_relevance", "why_relevant",
    "recommended_action", "confidence",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _markdown_pages(path: Path, *, pages: list[int] | None = None) -> list[dict[str, Any]]:
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RuntimeError(
            "Scientific PDF ingestion requires pymupdf4llm; install the project requirements."
        ) from exc
    result = pymupdf4llm.to_markdown(
        str(path), page_chunks=True, pages=pages, header=False, footer=False, use_ocr=False
    )
    if isinstance(result, str):
        return [{"text": result, "page": 1}]
    return [
        {"text": item.get("text", ""), "page": item.get("metadata", {}).get("page", i + 1)}
        for i, item in enumerate(result)
    ]


def extract_fast_context(path: Path) -> str:
    """Extract the opening four pages used for fast characterization."""
    pages = _markdown_pages(path, pages=[0, 1, 2, 3])
    text = "\n\n".join(page["text"] for page in pages)
    if len(text.strip()) < 4_000:
        # Born-digital PDFs are the baseline; OCR is deliberately not enabled
        # implicitly because it is slower and can damage scientific notation.
        return text[:MAX_CHARACTERIZATION_CHARS]
    return text[:MAX_CHARACTERIZATION_CHARS]


def _section_type(section: str) -> str:
    value = section.lower()
    groups = {
        "abstract": ("abstract",),
        "introduction": ("introduction",),
        "related_work": ("related work", "literature review"),
        "references": ("reference", "bibliography"),
        "methods": ("method", "algorithm", "formulation", "framework", "model"),
        "theory": ("theorem", "proof", "lemma", "bound", "analysis", "theory"),
        "experiments": ("experiment", "benchmark", "simulation", "numerical", "hardware"),
        "results": ("result", "evaluation", "finding"),
        "conclusion": ("conclusion", "future work"),
    }
    for name, terms in groups.items():
        if any(term in value for term in terms):
            return name
    return "other"


def _page_blocks(text: str, inherited: str = "Front Matter") -> tuple[list[tuple[str, str]], str]:
    section = inherited or "Front Matter"
    blocks: list[tuple[str, str]] = []
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            blocks.append((section, body))

    for line in text.splitlines():
        match = _HEADING_RE.match(line.strip())
        if match:
            flush()
            buffer.clear()
            candidate = re.sub(r"[*_`~]", "", match.group(2)).strip()
            if len(candidate) >= 4 and re.search(r"[A-Za-z]{3,}", candidate):
                section = candidate
            else:
                buffer.append(line)
        else:
            buffer.append(line)
    flush()
    return blocks, section


def chunk_pdf(path: Path, *, document_id: str | None = None,
              identity: dict[str, Any] | None = None) -> list[Chunk]:
    """Create page/section-aware chunks for a scientific PDF."""
    path = path.expanduser().resolve()
    document_id = document_id or sha256_file(path)
    identity = identity or {}
    chunks: list[Chunk] = []
    section = "Front Matter"
    index = 0
    for page in _markdown_pages(path):
        blocks, section = _page_blocks(page["text"], section)
        for name, body in blocks:
            breadcrumb = f"[{name}]\n" if name else ""
            pieces = split_plain(
                breadcrumb + body,
                str(path),
                size=settings.paper_chunk_size,
                overlap=settings.paper_chunk_overlap,
            )
            for piece in pieces:
                meta: dict[str, Any] = {
                    "filename": path.name,
                    "ext": ".pdf",
                    "doc_type": "research_paper",
                    "document_id": document_id,
                    "page": page["page"],
                    "section": name,
                    "section_type": _section_type(name),
                }
                for key in ("title", "authors", "doi", "arxiv_id", "year", "domain"):
                    if key in identity:
                        meta[key] = identity[key]
                chunks.append(Chunk(piece.text, str(path), index, meta))
                index += 1
    return chunks


def _prompt(text: str) -> str:
    return f"""You are Atelier's fast scientific-paper characterization worker.
Return only valid JSON with exactly these fields:
{', '.join(CHARACTERIZATION_FIELDS)}

Characterize only the supplied paper text. Domain and subfields must describe
the paper itself, not the user's interests. Set theoretical=true only for
formal theory, proofs, bounds, guarantees, or analytical derivations. Set
experimental=true for simulations, numerical studies, benchmarks, datasets,
or hardware experiments. Relevance values must be one of none, low, medium,
or high. recommended_action must be one of skip, skim, read, deep_read,
or reproduce. Do not invent missing identifiers.

The user's interests are AI, quantum computing, optimization, operations
research, mathematics, and scientific computing.

EXTRACTED PAPER TEXT:
{text[:MAX_CHARACTERIZATION_CHARS]}
"""


def characterize(path: Path) -> dict[str, Any]:
    """Characterize a paper with the local LFM worker and cache by file hash."""
    path = path.expanduser().resolve()
    document_id = sha256_file(path)
    settings.ensure_dirs()
    cache_path = settings.paper_metadata_dir / f"{document_id}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    from agent.brain import chat

    raw = chat(
        [{"role": "user", "content": _prompt(extract_fast_context(path))}],
        role="worker", temperature=0, json_mode=True,
    )
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Worker returned invalid paper JSON: {raw[:500]}") from exc
    missing = [field for field in CHARACTERIZATION_FIELDS if field not in result]
    if missing:
        raise RuntimeError(f"Worker paper card is missing fields: {', '.join(missing)}")
    result.update({"document_id": document_id, "source_filename": path.name, "path": str(path)})
    cache_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
