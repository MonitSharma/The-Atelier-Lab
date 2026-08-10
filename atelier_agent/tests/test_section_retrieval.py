from rag.retrieve import (
    _post_rank,
    _recent_candidates,
    recency_intent,
    reference_intent,
    source_date,
)


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


def test_recency_intent_and_filename_dates_are_explicit():
    assert recency_intent("what are the recent PIB updates")
    assert not recency_intent("explain the PIB update process")
    assert source_date({"source": "/tmp/PIB_2026-08-10.md"}).isoformat() == "2026-08-10"


def test_recent_queries_rank_newest_dated_sources_first():
    hits = _post_rank([
        _hit("older update", "other", 0.090, "PIB_2026-07-05.md"),
        _hit("newer update", "other", 0.010, "PIB_2026-08-08.md"),
        _hit("middle update", "other", 0.080, "PIB_2026-08-01.md"),
    ], "recent PIB updates", 3)

    assert [hit["metadata"]["source"] for hit in hits] == [
        "PIB_2026-08-08.md", "PIB_2026-08-01.md", "PIB_2026-07-05.md"
    ]


def test_recent_candidates_expand_to_new_dated_sources():
    class FakeStore:
        def get_all(self):
            return {
                "documents": ["July PIB", "August PIB", "Older quantum note"],
                "metadatas": [
                    {"source": "PIB_2026-07-05.md", "document_id": "july"},
                    {"source": "PIB_2026-08-08.md", "document_id": "august"},
                    {"source": "quantum_2026-08-09.md", "document_id": "quantum"},
                ],
            }

    candidates = _recent_candidates(FakeStore(), "recent PIB updates", limit=3)

    assert [item["metadata"]["source"] for item in candidates] == [
        "PIB_2026-08-08.md", "PIB_2026-07-05.md"
    ]
