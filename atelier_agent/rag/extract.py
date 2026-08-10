"""Local text extraction for document formats beyond plain text and PDF."""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


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


def _docx_sections(path: Path) -> list[tuple[str, dict[str, Any]]]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            return []
        root = ElementTree.fromstring(archive.read("word/document.xml"))
        paragraphs: list[str] = []
        for paragraph in root.iter():
            if _local_name(paragraph.tag) != "p":
                continue
            text = "".join(node.text or "" for node in paragraph.iter() if _local_name(node.tag) == "t").strip()
            if text:
                paragraphs.append(text)
        text = "\n\n".join(paragraphs)
        return [(text, {"format": "docx", "extraction": "office_xml"})] if text else []


def _pptx_sections(path: Path) -> list[tuple[str, dict[str, Any]]]:
    sections: list[tuple[str, dict[str, Any]]] = []
    with zipfile.ZipFile(path) as archive:
        slide_names = sorted(
            name for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        )
        for index, name in enumerate(slide_names, start=1):
            text = _xml_text(name, archive.read(name))
            if text:
                sections.append((text, {"format": "pptx", "extraction": "office_xml", "slide": index}))
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
    """Read safe, supported text members without extracting an archive."""
    allowed = {
        ".adoc", ".csv", ".json", ".log", ".markdown", ".md", ".mdx", ".org",
        ".py", ".rst", ".rs", ".sh", ".sql", ".tex", ".toml", ".ts", ".tsx",
        ".txt", ".xml", ".yaml", ".yml",
    }
    sections: list[tuple[str, dict[str, Any]]] = []
    with zipfile.ZipFile(path) as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            member = Path(info.filename)
            if info.is_dir() or member.suffix.lower() not in allowed or info.file_size > 5_000_000:
                continue
            text = archive.read(info).decode("utf-8", errors="replace").strip()
            if text:
                sections.append((text, {"format": "zip", "extraction": "archive_text", "member": info.filename}))
    return sections


def _ocr_image(path: Path) -> tuple[str, str]:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return "", "unavailable"
    try:
        result = subprocess.run(
            [tesseract, str(path), "stdout", "--psm", "11"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "", "failed"
    return result.stdout.strip(), "tesseract" if result.returncode == 0 else "failed"


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
        text, status = _ocr_image(resolved)
        if text:
            return [(text, {"format": "image", "extraction": status, "ocr": True})]
        warning = (
            "[Image has no extractable text. Install Tesseract or use a vision model for visual analysis.]"
        )
        return [(warning, {"format": "image", "extraction": status, "ocr": False})]
    return []
