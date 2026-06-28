import pytest
from foundation.datasets.builder.normalize import normalize_text

def test_unicode_nfc():
    # Devanagari combined characters (e.g. key characters + matras)
    # NFC will normalize it to single unified characters where possible
    raw_text = "क" + "\u093e" # क + ा (ka + matra)
    normalized = normalize_text(raw_text)
    assert len(normalized) == 2 # क is 1 character, ा is 1 character
    assert normalized == raw_text # In NFC, क + ा is already standard

def test_whitespace_collapsing():
    raw_text = "क   ख \t ग  "
    assert normalize_text(raw_text) == "क ख ग"

def test_blank_lines_collapsing():
    raw_text = "क\n\n\n\nख\n\nग"
    normalized = normalize_text(raw_text)
    assert normalized == "क\n\nख\n\nग"
