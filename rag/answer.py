"""Grounded question answering: retrieve, then synthesize with citations.

This is knowledge mode's payoff. The model is instructed to answer *only* from
the retrieved context and to cite the numbered sources, so we can measure
groundedness later (PROJECT.md §9) rather than trusting it blindly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.brain import chat
from rag.retrieve import citations, format_context, retrieve

GROUNDED_SYSTEM = """\
You are Atelier's knowledge assistant. Answer the user's question using ONLY the \
numbered context passages provided. Rules:
- If the answer is in the context, give it directly and cite sources like [1], [2].
- If the context does not contain the answer, say so plainly: "I don't find that \
in your notes." Do not invent facts or use outside knowledge.
- Be concise and concrete. Prefer the user's own wording when quoting.
"""


@dataclass
class Answer:
    text: str
    hits: list[dict[str, Any]]
    sources: list[str]


def answer_question(
    question: str,
    *,
    k: int | None = None,
    role: str = "brain",
    temperature: float | None = None,
) -> Answer:
    hits = retrieve(question, k=k)
    if not hits:
        return Answer(
            text="Your knowledge base is empty (or nothing matched). "
            "Run `atelier ingest <path>` first.",
            hits=[],
            sources=[],
        )
    context = format_context(hits)
    messages = [
        {"role": "system", "content": GROUNDED_SYSTEM},
        {
            "role": "user",
            "content": f"Context passages:\n\n{context}\n\n---\n\nQuestion: {question}",
        },
    ]
    text = chat(messages, role=role, temperature=temperature)
    return Answer(text=text, hits=hits, sources=citations(hits))
