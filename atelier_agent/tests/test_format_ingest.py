from zipfile import ZIP_DEFLATED, ZipFile

from rag.extract import extract_text_sections
from rag.ingest import SUPPORTED, chunk_file


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
