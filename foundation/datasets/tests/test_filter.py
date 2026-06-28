import pytest
from foundation.datasets.builder.filter import calculate_quality_score

def test_quality_score_devanagari_dominance():
    config = {
        "filters": {
            "min_chars": 5,
            "max_digit_ratio": 0.10,
            "max_punctuation_ratio": 0.15
        }
    }
    
    # Pure Sanskrit text
    sans_text = "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः"
    score, breakdown = calculate_quality_score(sans_text, config)
    assert score == 100
    assert breakdown["score_script"] == 30 # Full script score
    
    # Text mixed with English characters
    mixed_text = "धर्मक्षेत्रे कुरुक्षेत्रे english text"
    score_mixed, breakdown_mixed = calculate_quality_score(mixed_text, config)
    assert score_mixed < 100
    assert breakdown_mixed["score_script"] < 30 # Deducted due to Latin script presence

def test_quality_score_cleanliness():
    config = {
        "filters": {
            "min_chars": 5,
            "max_digit_ratio": 0.10,
            "max_punctuation_ratio": 0.15
        }
    }
    
    # Text with excessive punctuation/digits
    bad_text = "धर्मक्षेत्रे 123456789 !!!???@@@"
    score, breakdown = calculate_quality_score(bad_text, config)
    assert score < 100
    assert breakdown["score_clean"] < 30
