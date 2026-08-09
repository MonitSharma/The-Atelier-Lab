from rag.retrieve import _post_rank, reference_intent


def _hit(text, section, score, source="paper.pdf"):
    return {"text": text, "fused_score": score, "metadata": {
        "source": source, "document_id": source, "section_type": section,
    }}


def test_concept_query_penalizes_reference_dominance_and_diversifies():
    hits = _post_rank([
        _hit("reference one", "references", 0.040),
        _hit("reference two", "references", 0.039),
        _hit("quantum abstract", "abstract", 0.038),
        _hit("quantum methods", "methods", 0.037),
    ], "quantum", 3)
    assert hits[0]["text"] == "quantum abstract"
    assert all(hit["metadata"]["section_type"] != "references" for hit in hits[:2])


def test_reference_intent_keeps_references_eligible():
    assert reference_intent("papers and prior literature")
    hits = _post_rank([
        _hit("reference", "references", 0.035),
        _hit("abstract", "abstract", 0.040),
    ], "papers prior literature", 2)
    assert any(hit["metadata"]["section_type"] == "references" for hit in hits)
