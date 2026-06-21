"""Split documents into retrieval-sized, overlapping chunks.

Two strategies:

* :func:`split_markdown` — heading-aware. It tracks the heading stack so each
  chunk knows which ``# / ## / ###`` section it came from, and prepends that
  breadcrumb to the chunk text. This matters a lot for notes: a chunk that says
  "use bge-base" is far more retrievable when prefixed with
  "Knowledge mode > Embeddings".
* :func:`split_plain` — a paragraph-aware sliding window for everything else
  (txt, PDF page text, source code).

Both emit :class:`Chunk` records carrying enough metadata to cite the source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from atelier.config import settings

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    text: str
    source: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _window(text: str, size: int, overlap: int) -> list[str]:
    """Slide a window over text, preferring to break on blank lines.

    We accumulate paragraphs until adding the next would exceed ``size``, then
    emit a chunk and carry an ``overlap``-sized tail into the next one.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for para in paras:
        if len(para) > size:
            # A single huge paragraph: hard-split it.
            if cur:
                chunks.append(cur)
                cur = ""
            for i in range(0, len(para), size - overlap):
                chunks.append(para[i : i + size])
            continue
        if cur and len(cur) + len(para) + 2 > size:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap else ""
            cur = (tail + "\n\n" + para).strip()
        else:
            cur = f"{cur}\n\n{para}".strip() if cur else para
    if cur:
        chunks.append(cur)
    return chunks


def split_plain(
    text: str,
    source: str,
    *,
    base_meta: dict[str, Any] | None = None,
    size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    size = size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap
    base_meta = base_meta or {}
    out: list[Chunk] = []
    for i, piece in enumerate(_window(text, size, overlap)):
        out.append(Chunk(text=piece, source=source, chunk_index=i, metadata=dict(base_meta)))
    return out


def split_markdown(
    text: str,
    source: str,
    *,
    base_meta: dict[str, Any] | None = None,
    size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    size = size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap
    base_meta = base_meta or {}

    # Partition into (heading_path, body) sections.
    sections: list[tuple[str, str]] = []
    stack: list[tuple[int, str]] = []  # (level, title)
    buf: list[str] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            path = " > ".join(title for _, title in stack)
            sections.append((path, body))

    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            flush()
            buf = []
            level = len(m.group(1))
            title = m.group(2).strip()
            stack = [(lv, t) for lv, t in stack if lv < level]
            stack.append((level, title))
        else:
            buf.append(line)
    flush()

    out: list[Chunk] = []
    idx = 0
    for path, body in sections:
        for piece in _window(body, size, overlap):
            text_with_crumb = f"[{path}]\n{piece}" if path else piece
            meta = dict(base_meta)
            meta["section"] = path
            out.append(Chunk(text=text_with_crumb, source=source, chunk_index=idx, metadata=meta))
            idx += 1
    return out
