"""Deterministic PDF page-quality and figure/caption evidence."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from atelier.config import settings

_CAPTION_RE = re.compile(r"(?im)^\s*(?:figure|fig\.)\s+\d+[\.:\-]?\s+.+$")


@dataclass(frozen=True)
class PageEvidence:
    page: int
    characters: int
    quality: str
    captions: tuple[str, ...]
    citation: str
    rendered_image: str | None = None
    table_count: int = 0
    table_headers: tuple[str, ...] = ()
    ocr_status: str = "not_needed"
    ocr_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_pdf(
    path: str | Path, *, render: bool = False, output_dir: str | Path | None = None,
    ocr: bool = False,
) -> dict[str, Any]:
    """Return page citations, table hints, and optional scanned-page OCR.

    Native extraction remains authoritative. OCR is opt-in and its status is
    reported explicitly; it never replaces native text silently.
    """
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file() or resolved.suffix.lower() != ".pdf":
        raise ValueError(f"Expected an existing PDF file: {path}")
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise RuntimeError("PyMuPDF is required for PDF visual analysis.") from exc

    document = fitz.open(resolved)
    destination = Path(output_dir or settings.visual_cache_dir / resolved.stem)
    pages: list[PageEvidence] = []
    try:
        for index, page in enumerate(document, 1):
            text = page.get_text("text")
            captions = tuple(match.strip() for match in _CAPTION_RE.findall(text))
            replacement = text.count("�")
            quality = "poor" if len(text.strip()) < 80 or replacement > 3 else "good"
            needs_visual = render or quality == "poor" or bool(captions)
            image_path: str | None = None
            if needs_visual:
                destination.mkdir(parents=True, exist_ok=True)
                target = destination / f"page-{index:04d}.png"
                page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(target)
                image_path = str(target)
            table_count = 0
            table_headers: tuple[str, ...] = ()
            finder = getattr(page, "find_tables", None)
            if callable(finder):
                try:
                    tables = list(getattr(finder(), "tables", ()))
                    table_count = len(tables)
                    headers: list[str] = []
                    for table in tables:
                        header = getattr(table, "header", None)
                        names = getattr(header, "names", None) if header is not None else None
                        if isinstance(names, (list, tuple)):
                            headers.extend(str(name) for name in names if name is not None)
                    table_headers = tuple(dict.fromkeys(headers))
                except Exception:  # noqa: BLE001 - table extraction is optional evidence
                    table_count = 0
            ocr_status = "not_needed" if quality == "good" else "not_requested"
            ocr_text: str | None = None
            if quality == "poor" and ocr:
                try:
                    import pytesseract
                    from PIL import Image

                    if image_path is None:
                        destination.mkdir(parents=True, exist_ok=True)
                        target = destination / f"page-{index:04d}.png"
                        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(target)
                        image_path = str(target)
                    with Image.open(image_path) as image:
                        ocr_text = pytesseract.image_to_string(image)
                    ocr_status = "completed"
                except Exception as exc:  # noqa: BLE001 - report optional OCR failure
                    ocr_status = f"unavailable: {type(exc).__name__}"
            pages.append(PageEvidence(
                index, len(text), quality, captions, f"[p. {index}]", image_path,
                table_count, table_headers, ocr_status, ocr_text,
            ))
    finally:
        document.close()
    return {
        "path": str(resolved),
        "pages": [page.to_dict() for page in pages],
        "visual_fallback": any(page.quality == "poor" for page in pages),
        "figure_pages": [page.page for page in pages if page.captions],
    }
