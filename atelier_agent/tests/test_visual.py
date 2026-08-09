import pytest

from rag.visual import analyze_pdf


def test_pdf_visual_report_pairs_captions_and_citations(tmp_path) -> None:
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "paper.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Figure 1: A deterministic workflow\n" + "technical text " * 20)
    document.save(path)
    document.close()

    report = analyze_pdf(path, render=False)
    assert report["pages"][0]["citation"] == "[p. 1]"
    assert report["figure_pages"] == [1]
    assert report["pages"][0]["rendered_image"] is not None
    assert report["pages"][0]["ocr_status"] == "not_needed"
