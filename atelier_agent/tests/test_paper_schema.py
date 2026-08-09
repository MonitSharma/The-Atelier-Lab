import pytest

from rag.paper import PaperCharacterization, PaperExtraction, PaperIdentity


def test_paper_schema_requires_identity_and_characterization_fields():
    schema = PaperExtraction.model_json_schema()
    assert set(schema["required"]) == {"identity", "characterization"}
    assert set(PaperIdentity.model_json_schema()["required"]) >= {
        "title", "authors", "year", "doi", "arxiv_id", "document_type", "domain",
    }
    assert set(PaperCharacterization.model_json_schema()["required"]) >= {
        "theoretical", "experimental", "confidence",
    }


def test_paper_schema_rejects_unexpected_fields():
    with pytest.raises(Exception):
        PaperExtraction.model_validate({
            "identity": {"title": "x", "authors": [], "year": "", "doi": "", "arxiv_id": "", "document_type": "other", "domain": "", "venue": ""},
            "characterization": {"paper_type": "other", "subfields": [], "research_problem": "", "method": "", "main_claim": "", "theoretical": False, "experimental": False, "ai_relevance": "none", "quantum_relevance": "none", "optimization_relevance": "none", "why_relevant": "", "recommended_action": "skim", "confidence": "low"},
            "unexpected": True,
        })
