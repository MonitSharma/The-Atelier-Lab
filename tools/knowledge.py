"""search_notes tool — semantic retrieval over your indexed corpus.

This is what makes knowledge mode an *agent capability* rather than a separate
CLI path: the ReAct loop can call ``search_notes`` mid-task to pull grounded
facts from your own documents, then act on them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.base import Tool


def run_search_notes(arguments: dict[str, Any]) -> dict[str, Any]:
    query = arguments.get("query")
    k = arguments.get("k", 5)
    if not isinstance(query, str) or not query:
        return {"status": "error", "error_type": "invalid_arguments",
                "message": "search_notes requires a non-empty string 'query'."}
    if not isinstance(k, int) or k <= 0 or k > 20:
        k = 5

    # Imported lazily so tool registration doesn't load the embedding model.
    from rag.retrieve import retrieve

    try:
        hits = retrieve(query, k=k)
    except Exception as exc:  # noqa: BLE001 - surface store/model errors to the agent
        return {"status": "error", "error_type": "retrieval_error", "message": str(exc)}

    if not hits:
        return {"status": "success", "tool": "search_notes", "results": [],
                "message": "No matching passages. The knowledge base may be empty."}

    results = [
        {
            "source": Path(h["metadata"].get("source", "?")).name,
            "section": h["metadata"].get("section", ""),
            "score": round(float(h["score"]), 3),
            "text": h["text"][:1200],
        }
        for h in hits
    ]
    return {"status": "success", "tool": "search_notes", "results": results}


SEARCH_NOTES_TOOL = Tool(
    name="search_notes",
    description=(
        "Semantically search the user's indexed personal notes/docs/PDFs and "
        "return the most relevant passages with their source. Use this whenever "
        "a task depends on the user's own knowledge, decisions, or documents."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for, in natural language."},
            "k": {"type": "integer", "description": "How many passages to return (default 5)."},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    function=run_search_notes,
)
