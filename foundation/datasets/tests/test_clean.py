import pytest
from foundation.datasets.builder.clean import clean_document

def test_html_stripping():
    raw_text = "क <div>ख</div> ग <br/>"
    cleaned = clean_document(raw_text, {})
    assert cleaned == "क ख ग"

def test_markdown_stripping():
    raw_text = "## क **ख** [ग](http://example.com)"
    cleaned = clean_document(raw_text, {"filters": {"remove_headers": True}})
    assert cleaned == "क ख ग"

def test_wikipedia_edit_markers():
    raw_text = "क [सम्पादनं करोतु] ख [सम्पाद्यताम्] ग"
    cleaned = clean_document(raw_text, {})
    assert cleaned == "क ख ग"

def test_gretil_credits():
    raw_text = "GRETIL Text Files\nInput by Henil Patel\nक ख ग"
    cleaned = clean_document(raw_text, {"filters": {"remove_headers": True}})
    assert cleaned == "क ख ग"
