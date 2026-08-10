"""Local text extraction for document formats beyond plain text and PDF."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from posixpath import normpath
from typing import Any
from xml.etree import ElementTree

from atelier.config import settings
from rag.vision import VisionResult, analyze_image_bytes


class _VisibleHTML(HTMLParser):
    """Small dependency-free HTML-to-text reader for EPUB content documents."""

    _BLOCKS = {"article", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "section"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg"}:
            self.hidden += 1
        if self.hidden == 0 and tag in self._BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg"}:
            self.hidden = max(0, self.hidden - 1)
        if self.hidden == 0 and tag in self._BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.hidden == 0:
            self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self.parts)).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_text(path: str, payload: bytes) -> str:
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid XML in {path}: {exc}") from exc
    return " ".join(node.text or "" for node in root.iter() if _local_name(node.tag) in {"t", "text"}).strip()


def _node_text(node: ElementTree.Element) -> str:
    text_nodes = [item.text or "" for item in node.iter() if _local_name(item.tag) == "t"]
    if text_nodes:
        return "".join(text_nodes).strip()
    return "".join(
        [node.text or ""]
        + [item.text or "" for item in node.iter() if item is not node]
        + [item.tail or "" for item in node.iter()]
    ).strip()


def _vision_text(payload: bytes, *, citation: str) -> tuple[str, dict[str, Any]]:
    result: VisionResult = analyze_image_bytes(payload, citation=citation)
    metadata = result.to_metadata()
    metadata["human_review"] = result.human_review
    if result.text:
        return result.text, metadata
    return "[No visual description available; human review required.]", metadata


def _looks_like_image(payload: bytes) -> bool:
    return (
        payload.startswith(b"\x89PNG\r\n\x1a\n")
        or payload.startswith(b"\xff\xd8\xff")
        or payload.startswith((b"GIF87a", b"GIF89a"))
        or payload.startswith((b"II*\x00", b"MM\x00*"))
        or payload.startswith(b"RIFF") and payload[8:12] == b"WEBP"
        or payload.startswith(b"BM")
    )


def _office_media_sections(
    archive: zipfile.ZipFile,
    *,
    media_prefix: str,
    format_name: str,
    location_for: Any,
    member_prefix: str = "",
) -> list[tuple[str, dict[str, Any]]]:
    image_ext = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}
    sections: list[tuple[str, dict[str, Any]]] = []
    image_index = 0
    for name in sorted(archive.namelist()):
        suffix = Path(name).suffix.lower()
        if not name.startswith(media_prefix) or suffix not in image_ext:
            continue
        image_index += 1
        payload = archive.read(name)
        location = location_for(name)
        citation = f"{format_name} {location}; image {image_index}"
        text, vision_meta = _vision_text(payload, citation=citation)
        metadata: dict[str, Any] = {
            "format": format_name,
            "extraction": "embedded_image_vision",
            "image": True,
            "image_index": image_index,
            "image_member": f"{member_prefix}{name}",
            **vision_meta,
        }
        if isinstance(location, dict):
            metadata.update({key: value for key, value in location.items() if value is not None})
        sections.append((f"[Embedded image: {name}]\n{text}", metadata))
    return sections


def _docx_sections(path: Path) -> list[tuple[str, dict[str, Any]]]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            return []
        root = ElementTree.fromstring(archive.read("word/document.xml"))
        sections: list[tuple[str, dict[str, Any]]] = []
        heading = ""
        table_index = 0
        body = next((node for node in root.iter() if _local_name(node.tag) == "body"), root)
        for block in list(body):
            kind = _local_name(block.tag)
            if kind == "p":
                text = _node_text(block)
                if not text:
                    continue
                style = next((node for node in block.iter() if _local_name(node.tag) == "pStyle"), None)
                style_name = style.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "") if style is not None else ""
                if style_name.lower().startswith("heading"):
                    heading = text
                body_text = f"[Heading: {heading}]\n{text}" if heading and text != heading else text
                sections.append((body_text, {
                    "format": "docx", "extraction": "office_xml", "heading": heading,
                    "block": "paragraph", "style": style_name,
                }))
            elif kind == "tbl":
                table_index += 1
                rows: list[str] = []
                for _row_index, row in enumerate((n for n in block if _local_name(n.tag) == "tr"), start=1):
                    cells = []
                    for cell in (n for n in row if _local_name(n.tag) == "tc"):
                        cells.append(_node_text(cell))
                    if cells:
                        rows.append(" | ".join(cells))
                if rows:
                    sections.append((f"[Table {table_index}]\n" + "\n".join(rows), {
                        "format": "docx", "extraction": "office_xml", "heading": heading,
                        "block": "table", "table": table_index, "table_rows": len(rows),
                    }))
        sections.extend(_office_media_sections(
            archive, media_prefix="word/media/", format_name="docx",
            location_for=lambda _name: {"heading": heading} if heading else {},
        ))
        return sections


def _pptx_sections(path: Path) -> list[tuple[str, dict[str, Any]]]:
    sections: list[tuple[str, dict[str, Any]]] = []
    with zipfile.ZipFile(path) as archive:
        image_slides: dict[str, int] = {}
        slide_names = sorted(
            name for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        )
        for index, name in enumerate(slide_names, start=1):
            text = _xml_text(name, archive.read(name))
            if text:
                sections.append((text, {"format": "pptx", "extraction": "office_xml", "slide": index}))
            rels_name = f"ppt/slides/_rels/slide{index}.xml.rels"
            if rels_name in archive.namelist():
                rels_root = ElementTree.fromstring(archive.read(rels_name))
                for relation in rels_root.iter():
                    if _local_name(relation.tag) != "Relationship":
                        continue
                    target = relation.attrib.get("Target", "")
                    if "/media/" in target:
                        image_slides[normpath(f"ppt/slides/{target}").lstrip("/")] = index
        note_names = sorted(
            name for name in archive.namelist()
            if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)
        )
        for name in note_names:
            match = re.search(r"notesSlide(\d+)\.xml", name)
            slide = int(match.group(1)) if match else None
            text = _xml_text(name, archive.read(name))
            if text:
                sections.append((text, {
                    "format": "pptx", "extraction": "speaker_notes", "slide": slide,
                    "speaker_notes": True,
                }))
        sections.extend(_office_media_sections(
            archive, media_prefix="ppt/media/", format_name="pptx",
            location_for=lambda name: {"slide": image_slides.get(name)},
        ))
    return sections


def _xlsx_sections(path: Path) -> list[tuple[str, dict[str, Any]]]:
    """Extract visible cell values from modern Excel workbooks without executing them."""
    sections: list[tuple[str, dict[str, Any]]] = []
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.iter():
                if _local_name(item.tag) == "si":
                    shared.append("".join(node.text or "" for node in item.iter() if _local_name(node.tag) == "t"))
        sheet_names = sorted(name for name in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
        for index, name in enumerate(sheet_names, start=1):
            root = ElementTree.fromstring(archive.read(name))
            values: list[str] = []
            for cell in root.iter():
                if _local_name(cell.tag) != "c":
                    continue
                kind = cell.attrib.get("t", "")
                value_node = next((node for node in cell if _local_name(node.tag) == "v"), None)
                if value_node is None or value_node.text is None:
                    continue
                value = value_node.text
                if kind == "s" and value.isdigit() and int(value) < len(shared):
                    value = shared[int(value)]
                values.append(value)
            if values:
                sections.append(("\t".join(values), {"format": "xlsx", "extraction": "office_xml", "sheet": index}))
    return sections


def _epub_sections(path: Path) -> list[tuple[str, dict[str, Any]]]:
    sections: list[tuple[str, dict[str, Any]]] = []
    with zipfile.ZipFile(path) as archive:
        content_names = sorted(
            name for name in archive.namelist()
            if Path(name).suffix.lower() in {".html", ".htm", ".xhtml"}
        )
        for index, name in enumerate(content_names, start=1):
            parser = _VisibleHTML()
            parser.feed(archive.read(name).decode("utf-8", errors="replace"))
            text = parser.text()
            if text:
                sections.append((text, {"format": "epub", "extraction": "html", "member": name, "section": index}))
    return sections


def _archive_sections(path: Path) -> list[tuple[str, dict[str, Any]]]:
    """Recursively read safe archive members without extracting to disk."""
    allowed = {
        ".adoc", ".csv", ".json", ".log", ".markdown", ".md", ".mdx", ".org",
        ".py", ".rst", ".rs", ".sh", ".sql", ".tex", ".toml", ".ts", ".tsx",
        ".txt", ".xml", ".yaml", ".yml",
    }
    sections: list[tuple[str, dict[str, Any]]] = []
    counters = {"members": 0, "bytes": 0}

    def warning(member: str, reason: str) -> None:
        sections.append((f"[Archive member skipped: {member}] {reason}", {
            "format": "zip", "extraction": "archive_skipped", "archive_member": member,
            "human_review": True, "archive_skip_reason": reason,
        }))

    def walk(payload: bytes, prefix: str, depth: int) -> None:
        if depth > settings.archive_max_depth:
            warning(prefix or path.name, "maximum archive nesting depth exceeded")
            return
        try:
            archive = zipfile.ZipFile(BytesIO(payload))
        except zipfile.BadZipFile:
            warning(prefix or path.name, "invalid nested ZIP")
            return
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            counters["members"] += 1
            member_name = f"{prefix}/{info.filename}" if prefix else info.filename
            member = Path(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if counters["members"] > settings.archive_max_members:
                warning(member_name, "maximum member count exceeded")
                return
            if info.is_dir() or member.is_absolute() or ".." in member.parts or mode == 0o120000:
                warning(member_name, "unsafe member path or symlink skipped")
                continue
            if info.flag_bits & 0x1:
                warning(member_name, "encrypted member skipped")
                continue
            if info.file_size > settings.archive_max_member_bytes:
                warning(member_name, "member exceeds size limit")
                continue
            if info.compress_size and info.file_size / info.compress_size > settings.archive_max_compression_ratio:
                warning(member_name, "compression ratio exceeds security limit")
                continue
            counters["bytes"] += info.file_size
            if counters["bytes"] > settings.archive_max_total_bytes:
                warning(member_name, "archive total size limit exceeded")
                return
            suffix = member.suffix.lower()
            raw = archive.read(info)
            if suffix == ".zip":
                walk(raw, member_name, depth + 1)
                continue
            if suffix in allowed:
                text = raw.decode("utf-8", errors="replace").strip()
                if text:
                    sections.append((text, {
                        "format": "zip", "extraction": "archive_text", "member": member_name,
                        "archive_member": member_name, "archive_depth": depth,
                    }))
                continue
            if suffix in {".docx", ".pptx", ".xlsx", ".xlsm", ".epub", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}:
                with tempfile.NamedTemporaryFile(suffix=suffix) as temporary:
                    temporary.write(raw)
                    temporary.flush()
                    nested_sections = extract_text_sections(temporary.name)
                for text, metadata in nested_sections:
                    metadata = dict(metadata)
                    metadata.update({"archive_member": member_name, "member": member_name, "archive_depth": depth})
                    sections.append((text, metadata))

    walk(path.read_bytes(), "", 0)
    return sections


def _ocr_image(path: Path) -> tuple[str, str, float | None, bool]:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return "", "unavailable", None, True
    try:
        result = subprocess.run(
            [tesseract, str(path), "stdout", "--psm", "11", "tsv"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "", "failed", None, True
    words: list[str] = []
    confidences: list[float] = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) < 12 or not fields[11].strip():
            continue
        words.append(fields[11].strip())
        try:
            value = float(fields[10])
            if value >= 0:
                confidences.append(value / 100.0)
        except ValueError:
            continue
    text = " ".join(words).strip()
    confidence = sum(confidences) / len(confidences) if confidences else None
    review = confidence is None or confidence < settings.ocr_review_threshold
    return text, "tesseract" if result.returncode == 0 else "failed", confidence, review


def extract_text_sections(path: str | Path) -> list[tuple[str, dict[str, Any]]]:
    """Extract text sections while keeping format/member metadata for citations."""
    resolved = Path(path).expanduser().resolve()
    suffix = resolved.suffix.lower()
    if suffix == ".docx":
        return _docx_sections(resolved)
    if suffix == ".pptx":
        return _pptx_sections(resolved)
    if suffix in {".xlsx", ".xlsm"}:
        return _xlsx_sections(resolved)
    if suffix == ".epub":
        return _epub_sections(resolved)
    if suffix == ".zip":
        return _archive_sections(resolved)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}:
        payload = resolved.read_bytes()
        text, status, confidence, review = _ocr_image(resolved)
        if _looks_like_image(payload):
            vision_text, vision_meta = _vision_text(payload, citation=f"image {resolved.name}")
        else:
            vision_text, vision_meta = "", {"vision_status": "invalid_image", "vision_human_review": True}
        pieces: list[str] = []
        if text:
            pieces.append(f"[OCR transcription]\n{text}")
        if vision_text and not vision_text.startswith("[No visual"):
            pieces.append(f"[Vision analysis]\n{vision_text}")
        if not pieces:
            pieces.append("[Image has no extractable text or visual description. Install Tesseract or configure the local vision model.]" )
        metadata = {
            "format": "image", "extraction": f"{status}+vision", "ocr": bool(text),
            "ocr_confidence": confidence if confidence is not None else -1.0, "ocr_human_review": review,
            "human_review": review or vision_meta.get("vision_human_review", True),
            **vision_meta,
        }
        return [("\n\n".join(pieces), metadata)]
    return []
