from rag.paper import clean_retrieval_text, section_type


def test_conservative_pdf_cleanup_removes_picture_boilerplate():
    raw = "Abstract\n**==> picture [1] intentionally omitted <==**\nCaption remains\n<br>next"
    cleaned = clean_retrieval_text(raw)
    assert "picture" not in cleaned.lower()
    assert "Caption remains" in cleaned
    assert "<br>" not in cleaned


def test_section_types_include_front_matter_and_references():
    assert section_type("Front Matter") == "front_matter"
    assert section_type("References") == "references"
    assert section_type("Discussion and Limitations") == "discussion"
    assert section_type("Unclear Heading") == "other"
