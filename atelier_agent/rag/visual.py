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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_pdf(path: str | Path, *, render: bool = False, output_dir: str | Path | None = None) -> dict[str, Any]:
    """Return page citations and render only pages needing visual fallback."""
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
            pages.append(PageEvidence(index, len(text), quality, captions, f"[p. {index}]", image_path))
    finally:
        document.close()
    return {
        "path": str(resolved),
        "pages": [page.to_dict() for page in pages],
        "visual_fallback": any(page.quality == "poor" for page in pages),
        "figure_pages": [page.page for page in pages if page.captions],
    }
