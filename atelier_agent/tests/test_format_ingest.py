from zipfile import ZIP_DEFLATED, ZipFile

from rag.extract import extract_text_sections
from rag.ingest import SUPPORTED, chunk_file
from rag.retrieve import citations, format_context
from rag.vision import VisionResult


def _zip_file(path, members: dict[str, str]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, text in members.items():
            archive.writestr(name, text)


def test_docx_text_is_extracted_from_office_xml(tmp_path) -> None:
    path = tmp_path / "notes.docx"
    _zip_file(path, {
        "word/document.xml": (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Research question</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>Test the hypothesis.</w:t></w:r></w:p></w:body></w:document>"
        )
    })

    chunks = chunk_file(path)

    assert "Research question" in chunks[0].text
    assert chunks[0].metadata["format"] == "docx"
    assert chunks[0].metadata["doc_type"] == "document"


def test_pptx_epub_and_zip_text_are_indexable(tmp_path) -> None:
    pptx = tmp_path / "slides.pptx"
    _zip_file(pptx, {
        "ppt/slides/slide1.xml": '<p:sld xmlns:p="p" xmlns:a="a"><a:t>Slide finding</a:t></p:sld>',
    })
    epub = tmp_path / "book.epub"
    _zip_file(epub, {"OEBPS/chapter.xhtml": "<h1>Chapter</h1><p>Book text.</p>"})
    archive = tmp_path / "notes.zip"
    _zip_file(archive, {"notes/idea.md": "# Idea\n\nArchive text."})

    assert "Slide finding" in chunk_file(pptx)[0].text
    assert "Book text." in chunk_file(epub)[0].text
    assert "Archive text." in chunk_file(archive)[0].text
    assert {".docx", ".pptx", ".epub", ".zip", ".png"} <= SUPPORTED


def test_image_without_ocr_engine_still_produces_a_local_warning(tmp_path, monkeypatch) -> None:
    image = tmp_path / "handwritten.png"
    image.write_bytes(b"not-a-real-image")
    monkeypatch.setattr("rag.extract.shutil.which", lambda _: None)

    sections = extract_text_sections(image)

    assert sections[0][1]["ocr"] is False
    assert "vision model" in sections[0][0]


def test_docx_preserves_headings_tables_and_embedded_image_citations(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "rag.extract.analyze_image_bytes",
        lambda payload, citation: VisionResult(
            "DESCRIPTION: handwritten equation x^2 + 1", "fake-vision", 0.91, False, "completed"
        ),
    )
    path = tmp_path / "research.docx"
    _zip_file(path, {
        "word/document.xml": (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:pPr><w:pStyle w:val='Heading1'/></w:pPr>Methods</w:p>"
            "<w:p>Freeze the encoder.</w:p><w:tbl><w:tr><w:tc><w:p>Metric</w:p></w:tc>"
            "<w:tc><w:p>AULC</w:p></w:tc></w:tr></w:tbl></w:body></w:document>"
        ),
        "word/media/image1.png": b"\x89PNG\r\n\x1a\nvalid-enough-for-mock",
    })

    sections = extract_text_sections(path)
    assert any(meta.get("heading") == "Methods" for _, meta in sections)
    assert any(meta.get("table") == 1 for _, meta in sections)
    image = next((meta for _, meta in sections if meta.get("image")), None)
    assert image is not None
    assert image["image_member"] == "word/media/image1.png"
    assert image["vision_confidence"] == 0.91


def test_pptx_preserves_speaker_notes_and_slide_image_locations(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "rag.extract.analyze_image_bytes",
        lambda payload, citation: VisionResult("DESCRIPTION: circuit diagram", "fake-vision", 0.8, False, "completed"),
    )
    path = tmp_path / "deck.pptx"
    _zip_file(path, {
        "ppt/slides/slide1.xml": '<p:sld xmlns:p="p" xmlns:a="a"><a:t>Finding</a:t></p:sld>',
        "ppt/slides/_rels/slide1.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="../media/image1.png" Type="image"/></Relationships>'
        ),
        "ppt/notesSlides/notesSlide1.xml": '<p:notes xmlns:p="p" xmlns:a="a"><a:t>Say this aloud</a:t></p:notes>',
        "ppt/media/image1.png": b"\x89PNG\r\n\x1a\nvalid-enough-for-mock",
    })

    sections = extract_text_sections(path)
    assert any(meta.get("speaker_notes") and meta.get("slide") == 1 for _, meta in sections)
    assert any(meta.get("image") and meta.get("slide") == 1 for _, meta in sections)


def test_nested_archive_members_are_cited_and_security_limited(tmp_path) -> None:
    nested = tmp_path / "nested.zip"
    _zip_file(nested, {"inner/notes.md": "Nested finding"})
    path = tmp_path / "bundle.zip"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("nested.zip", nested.read_bytes())
        archive.writestr("../unsafe.md", "do not read")

    sections = extract_text_sections(path)
    nested_section = next((meta for text, meta in sections if "Nested finding" in text), None)
    assert nested_section is not None
    assert nested_section["archive_member"] == "nested.zip/inner/notes.md"
    assert any(meta.get("archive_skip_reason") for _, meta in sections)


def test_retrieval_citations_preserve_page_slide_table_and_archive_locations() -> None:
    hits = [{
        "text": "evidence",
        "metadata": {
            "source": "/tmp/plan.docx", "page": 3, "slide": 2, "table": 1,
            "archive_member": "nested/plan.docx",
        },
    }]
    context = format_context(hits)
    assert "p. 3" in context and "slide 2" in context and "table 1" in context
    assert "archive: nested/plan.docx" in context
    assert "p. 3" in citations(hits)[0]
