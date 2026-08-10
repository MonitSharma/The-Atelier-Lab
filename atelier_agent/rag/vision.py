"""Local multimodal analysis through the installed Ollama vision model.

The vision path is deliberately separate from text extraction. Native text and
OCR remain the primary evidence; the vision model adds descriptions for
handwriting, diagrams, equations, and image-only pages and reports uncertainty
so the caller can require human review.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atelier.config import settings


@dataclass(frozen=True)
class VisionResult:
    text: str
    model: str
    confidence: float | None
    human_review: bool
    status: str

    def to_metadata(self) -> dict[str, Any]:
        return {
            "vision_model": self.model,
            "vision_confidence": self.confidence if self.confidence is not None else -1.0,
            "vision_human_review": self.human_review,
            "vision_status": self.status,
        }


_CONFIDENCE_RE = re.compile(r"(?:VISUAL[_ ]CONFIDENCE|CONFIDENCE)\s*:\s*(0(?:\.\d+)?|1(?:\.0+)?)", re.I)
_REVIEW_RE = re.compile(r"(?:HUMAN[_ ]REVIEW|REVIEW)\s*:\s*(yes|no|true|false)", re.I)


def _parse_response(text: str) -> tuple[str, float | None, bool]:
    confidence_match = _CONFIDENCE_RE.search(text)
    confidence = float(confidence_match.group(1)) if confidence_match else None
    review_match = _REVIEW_RE.search(text)
    review = review_match is None or review_match.group(1).lower() in {"yes", "true"}
    cleaned = _CONFIDENCE_RE.sub("", text)
    cleaned = _REVIEW_RE.sub("", cleaned)
    return cleaned.strip(), confidence, review


def _prompt(citation: str) -> str:
    return f"""You are Atelier's local document-vision analyst.
Inspect the supplied image and produce evidence for a research knowledge base.
Describe diagrams, plots, tables, handwriting, symbols, and equations. Transcribe
visible equations in LaTeX when possible, preserving variables and operators.
Never guess illegible content: write [unclear] and explain what needs checking.
Keep the answer concise and cite the image location as {citation}.
Start with exactly these two lines:
VISUAL_CONFIDENCE: <number from 0 to 1>
HUMAN_REVIEW: <yes or no>
Then provide labelled sections DESCRIPTION, TRANSCRIPTION, and UNCERTAINTIES.
"""


def analyze_image_bytes(
    payload: bytes,
    *,
    citation: str = "embedded image",
    model: str | None = None,
) -> VisionResult:
    """Analyze image bytes with the configured local Ollama vision model."""
    model_name = model or settings.vision_model
    if not settings.vision_enabled:
        return VisionResult("", model_name, None, True, "disabled")
    if len(payload) > settings.vision_max_image_bytes:
        return VisionResult("", model_name, None, True, "image_too_large")
    try:
        import ollama

        client = ollama.Client(host=settings.ollama_url)
        response = client.chat(
            model=model_name,
            messages=[{
                "role": "user",
                "content": _prompt(citation),
                "images": [base64.b64encode(payload).decode("ascii")],
            }],
            options={"temperature": 0},
            stream=False,
        )
        raw = response.get("message", {}).get("content", "")
        if not raw:
            return VisionResult("", model_name, None, True, "empty_response")
        text, confidence, review = _parse_response(str(raw))
        if confidence is not None and confidence < settings.vision_review_threshold:
            review = True
        return VisionResult(text, model_name, confidence, review, "completed")
    except Exception as exc:  # noqa: BLE001 - ingestion records optional vision failures
        return VisionResult("", model_name, None, True, f"unavailable:{type(exc).__name__}")


def analyze_image(path: str | Path, *, citation: str = "image") -> VisionResult:
    resolved = Path(path).expanduser().resolve()
    try:
        payload = resolved.read_bytes()
    except OSError as exc:
        return VisionResult("", settings.vision_model, None, True, f"read_failed:{type(exc).__name__}")
    return analyze_image_bytes(payload, citation=citation)
