"""Content-addressed scientific PDF extraction and paper metadata."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from atelier.config import settings
from rag.chunk import Chunk, split_plain

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
MAX_CHARACTERIZATION_CHARS = 18_000
SECTION_TYPES = {
    "front_matter", "abstract", "introduction", "related_work", "methods",
    "theory", "experiments", "results", "discussion", "conclusion",
    "references", "appendix", "other",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaperIdentity(StrictModel):
    title: str
    authors: list[str]
    year: str
    doi: str
    arxiv_id: str
    document_type: Literal[
        "research_paper", "review", "survey", "book", "thesis", "report",
        "technical_note", "other",
    ]
    domain: str
    venue: str


class PaperCharacterization(StrictModel):
    paper_type: Literal[
        "theoretical", "experimental", "theoretical_and_experimental", "review",
        "survey", "methods", "other",
    ]
    subfields: list[str] = Field(max_length=5)
    research_problem: str
    method: str
    main_claim: str
    theoretical: bool
    experimental: bool
    ai_relevance: Literal["none", "low", "medium", "high"]
    quantum_relevance: Literal["none", "low", "medium", "high"]
    optimization_relevance: Literal["none", "low", "medium", "high"]
    why_relevant: str
    recommended_action: Literal["skip", "skim", "read", "deep_read", "reproduce"]
    confidence: Literal["low", "medium", "high"]


class PaperExtraction(StrictModel):
    identity: PaperIdentity
    characterization: PaperCharacterization


def _sanitize_identity(values: dict[str, Any]) -> dict[str, Any]:
    """Reject identifier-shaped hallucinations conservatively at the boundary."""
    cleaned = dict(values)
    arxiv = str(cleaned.get("arxiv_id", "")).strip()
    if arxiv and not re.fullmatch(r"(?:arxiv:)?\d{4}\.\d{4,5}(?:v\d+)?", arxiv, re.I):
        cleaned["arxiv_id"] = ""
    return cleaned


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_retrieval_text(text: str) -> str:
    """Remove extractor boilerplate while leaving scientific content intact."""
    text = text.replace("\x00", "")
    text = re.sub(
        r"(?is)\*{0,2}==>\s*picture.*?intentionally omitted\s*<==\*{0,2}\s*",
        "",
        text,
    )
    text = re.sub(r"(?is)-{3,}\s*Start of picture text\s*-{3,}.*?-{3,}\s*End of picture text\s*-{3,}", "", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    # Replacement glyphs are extractor noise when isolated; do not perform
    # broad spell correction or rewrite equation-like text.
    text = text.replace("\ufffd", "")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pages(path: Path) -> list[dict[str, Any]]:
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise RuntimeError(
            "Scientific PDF ingestion requires pymupdf4llm; install the project requirements."
        ) from exc
    result = pymupdf4llm.to_markdown(
        str(path), page_chunks=True, header=False, footer=False, use_ocr=False
    )
    if isinstance(result, str):
        result = [{"text": result, "metadata": {"page": 1}}]
    pages: list[dict[str, Any]] = []
    for index, item in enumerate(result, start=1):
        raw = item.get("text", "")
        metadata = item.get("metadata", {}) or {}
        page_number = metadata.get("page", index)
        text = clean_retrieval_text(raw)
        extraction = "native"
        if len(text) < 40:
            ocr_text = _ocr_pdf_page(path, int(page_number))
            if len(ocr_text) > len(text):
                text = clean_retrieval_text(ocr_text)
                extraction = "tesseract_ocr"
        pages.append({
            "page": page_number,
            "raw_text": raw,
            "text": text,
            "extraction": extraction,
        })
    return pages


def _ocr_pdf_page(path: Path, page_number: int) -> str:
    """Best-effort OCR for image-only or handwritten PDF pages."""
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return ""
    try:
        import fitz

        document = fitz.open(path)
        page = document.load_page(max(0, page_number - 1))
        longest_side = max(float(page.rect.width), float(page.rect.height))
        scale = min(2.0, max(1.0, 5000.0 / max(longest_side, 1.0)))
        pixels = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        result = subprocess.run(
            [tesseract, "stdin", "stdout", "--psm", "11"],
            input=pixels.tobytes("png"),
            capture_output=True,
            text=False,
            timeout=120,
            check=False,
        )
        return result.stdout.decode("utf-8", errors="replace").strip() if result.returncode == 0 else ""
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
        return ""


def extract_pdf_pages(path: Path, document_id: str | None = None) -> list[dict[str, Any]]:
    """Return cached raw/retrieval page text, keyed by content hash."""
    path = path.expanduser().resolve()
    document_id = document_id or sha256_file(path)
    settings.ensure_dirs()
    cache_path = settings.extracted_dir / f"{document_id}.json"
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") == 2 and payload.get("document_id") == document_id:
            return payload.get("pages", [])
    pages = _extract_pages(path)
    cache_path.write_text(
        json.dumps({"schema_version": 2, "document_id": document_id, "pages": pages},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    return pages


def extract_fast_context(path: Path) -> str:
    document_id = sha256_file(path)
    pages = extract_pdf_pages(path, document_id)[:4]
    return "\n\n".join(page["text"] for page in pages)[:MAX_CHARACTERIZATION_CHARS]


def section_type(section: str) -> str:
    value = section.strip().lower()
    if not value or value in {"front matter", "front_matter"}:
        return "front_matter"
    groups = {
        "abstract": ("abstract",),
        "introduction": ("introduction",),
        "related_work": ("related work", "related literature", "literature review", "prior work"),
        "references": ("reference", "bibliography"),
        "appendix": ("appendix", "supplement"),
        "conclusion": ("conclusion", "future work"),
        "discussion": ("discussion", "limitation", "implication"),
        "theory": ("theorem", "proof", "lemma", "bound", "analysis", "theory"),
        "experiments": ("experiment", "benchmark", "simulation", "numerical", "hardware", "protocol"),
        "results": ("result", "evaluation", "finding"),
        "methods": ("method", "algorithm", "formulation", "framework", "architecture", "implementation"),
    }
    for name, terms in groups.items():
        if any(term in value for term in terms):
            return name
    return "other"


def _page_blocks(text: str, inherited: str = "Front Matter") -> tuple[list[tuple[str, str]], str]:
    current = inherited or "Front Matter"
    blocks: list[tuple[str, str]] = []
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            blocks.append((current, body))

    for line in text.splitlines():
        match = _HEADING_RE.match(line.strip())
        if match:
            flush()
            buffer.clear()
            candidate = re.sub(r"[*_`~]", "", match.group(2)).strip()
            if len(candidate) >= 4 and re.search(r"[A-Za-z]{3,}", candidate):
                current = candidate
            else:
                buffer.append(line)
        else:
            buffer.append(line)
    flush()
    return blocks, current


def _identity_dict(identity: dict[str, Any] | PaperIdentity | None) -> dict[str, Any]:
    if isinstance(identity, PaperIdentity):
        return identity.model_dump()
    return dict(identity or {})


def chunk_pdf(path: Path, *, document_id: str | None = None,
              identity: dict[str, Any] | PaperIdentity | None = None) -> list[Chunk]:
    """Create page/section-aware retrieval chunks for a scientific PDF."""
    path = path.expanduser().resolve()
    document_id = document_id or sha256_file(path)
    identity_data = _identity_dict(identity)
    chunks: list[Chunk] = []
    current_section = "Front Matter"
    index = 0
    for page in extract_pdf_pages(path, document_id):
        blocks, current_section = _page_blocks(page["text"], current_section)
        for raw_section, body in blocks:
            pieces = split_plain(
                f"[{raw_section}]\n{body}", str(path),
                size=settings.paper_chunk_size, overlap=settings.paper_chunk_overlap,
            )
            for piece in pieces:
                metadata: dict[str, Any] = {
                    "filename": path.name,
                    "ext": ".pdf",
                    "doc_type": "research_paper",
                    "document_id": document_id,
                    "page": page["page"],
                    "section": raw_section,
                    "section_type": section_type(raw_section),
                    "metadata_schema_version": settings.metadata_schema_version,
                }
                for key in ("title", "authors", "year", "doi", "arxiv_id", "document_type", "domain", "venue"):
                    if key in identity_data:
                        metadata[key] = identity_data[key]
                chunks.append(Chunk(piece.text, str(path), index, metadata))
                index += 1
    return chunks


def _legacy_to_structured(payload: dict[str, Any], document_id: str, path: Path) -> dict[str, Any]:
    if "identity" in payload and "characterization" in payload:
        return payload
    identity = {
        "title": payload.get("title", ""), "authors": payload.get("authors", []),
        "year": payload.get("year", ""), "doi": payload.get("doi", ""),
        "arxiv_id": payload.get("arxiv_id", ""), "document_type": payload.get("document_type", "other"),
        "domain": payload.get("domain", ""), "venue": payload.get("venue", ""),
    }
    characterization_defaults = {
        "paper_type": "other", "subfields": [], "research_problem": "",
        "method": "", "main_claim": "", "theoretical": False, "experimental": False,
        "ai_relevance": "none", "quantum_relevance": "none",
        "optimization_relevance": "none", "why_relevant": "",
        "recommended_action": "skim", "confidence": "low",
    }
    characterization = {
        key: payload.get(key, default)
        for key, default in characterization_defaults.items()
    }
    return {"schema_version": settings.metadata_schema_version, "document_id": document_id,
            "identity": identity, "characterization": characterization,
            "legacy_source_filename": path.name}


def load_metadata(path: Path, document_id: str | None = None) -> PaperExtraction | None:
    path = path.expanduser().resolve()
    document_id = document_id or sha256_file(path)
    cache_path = settings.paper_metadata_dir / f"{document_id}.json"
    if not cache_path.exists():
        return None
    raw_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    if "characterization" not in raw_payload and not {
        "paper_type", "research_problem", "method", "main_claim"
    }.issubset(raw_payload):
        # Older workbench caches contained identity only. They are useful for
        # chunk metadata but are not a complete Fast Paper card.
        return None
    payload = _legacy_to_structured(raw_payload, document_id, path)
    try:
        return PaperExtraction(
            identity=PaperIdentity.model_validate(_sanitize_identity(payload.get("identity", {}))),
            characterization=PaperCharacterization.model_validate(payload.get("characterization", {})),
        )
    except ValidationError:
        return None


def _prompt(text: str) -> str:
    return f"""You are Atelier's fast scientific-paper characterization worker.
Return an object with exactly two fields: identity and characterization.
Identity describes only facts present in the supplied paper. Never infer
identity from the filename. Use empty strings/lists for missing identifiers.
Characterization describes the paper and its relevance to AI, quantum
computing, optimization, operations research, mathematics, and scientific
computing. Do not invent facts.

PAPER TEXT:
{text[:MAX_CHARACTERIZATION_CHARS]}
"""


def characterize(path: Path) -> dict[str, Any]:
    """Run strict LFM extraction once per content hash and cache only valid output."""
    path = path.expanduser().resolve()
    document_id = sha256_file(path)
    settings.ensure_dirs()
    existing = load_metadata(path, document_id)
    if existing is not None:
        payload = {"schema_version": settings.metadata_schema_version, "document_id": document_id,
                   "identity": existing.identity.model_dump(),
                   "characterization": existing.characterization.model_dump()}
        cache_path = settings.paper_metadata_dir / f"{document_id}.json"
        if json.loads(cache_path.read_text(encoding="utf-8")) != payload:
            cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return payload

    from agent.brain import chat

    raw = chat(
        [{"role": "user", "content": _prompt(extract_fast_context(path))}],
        role="worker", temperature=0, json_mode=True,
        json_schema=PaperExtraction.model_json_schema(),
    )
    try:
        parsed = PaperExtraction.model_validate_json(raw)
    except (ValidationError, ValueError) as exc:
        raise RuntimeError(f"Worker returned invalid paper metadata; cache not written: {exc}") from exc
    identity = PaperIdentity.model_validate(_sanitize_identity(parsed.identity.model_dump()))
    payload = {"schema_version": settings.metadata_schema_version, "document_id": document_id,
               "identity": identity.model_dump(),
               "characterization": parsed.characterization.model_dump()}
    (settings.paper_metadata_dir / f"{document_id}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return payload
