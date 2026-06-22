"""The brain: a thin, robust client over the local Ollama server.

Upgrades over the Phase-0 urllib version:
  * uses the official ``ollama`` client (connection reuse, cleaner errors);
  * model *roles* (brain / worker / heavy) resolved from config, so callers ask
    for the right *size* of model rather than hard-coding a name;
  * optional JSON-only output mode for structured tool calls;
  * streaming for interactive use;
  * handles qwen3-style ``<think>...</think>`` traces (kept out of parsed output).

Nothing here leaves the machine — it talks only to ``localhost:11434``.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterator
from typing import Any, Literal

import httpx
import ollama

from atelier.config import settings

Role = Literal["brain", "worker", "heavy"]

_MODEL_BY_ROLE: dict[str, str] = {
    "brain": settings.brain_model,
    "worker": settings.worker_model,
    "heavy": settings.heavy_model,
}

_client = ollama.Client(host=settings.ollama_url)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class BrainError(RuntimeError):
    """Raised when the local model cannot be reached or returns nothing usable."""


def _resolve_model(model: str | None, role: Role) -> str:
    if model:
        return model
    return _MODEL_BY_ROLE.get(role, settings.brain_model)


def strip_thinking(text: str) -> str:
    """Remove qwen3 ``<think>`` reasoning so downstream sees only the answer.

    Handles three shapes seen in the wild: properly paired ``<think>..</think>``,
    an orphan closing tag (open tag delivered out-of-band), and a trailing
    unclosed ``<think>`` block.
    """
    text = _THINK_RE.sub("", text)
    if "</think>" in text:  # orphan close: keep only what follows the last one
        text = text.rsplit("</think>", 1)[-1]
    text = text.replace("<think>", "").replace("</think>", "")
    return text.strip()


def _options(temperature: float | None) -> dict[str, Any]:
    return {"temperature": settings.temperature if temperature is None else temperature}


def chat(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    role: Role = "brain",
    temperature: float | None = None,
    json_mode: bool = False,
    think: bool = False,
) -> str:
    """Send a conversation and return the assistant's text.

    ``role`` selects the model size when ``model`` is not given explicitly.
    ``json_mode`` constrains the model to emit valid JSON (used for tool calls).
    ``think`` toggles qwen3 reasoning traces; off by default for clean output.
    """
    name = _resolve_model(model, role)
    kwargs: dict[str, Any] = {
        "model": name,
        "messages": messages,
        "options": _options(temperature),
        "stream": False,
    }
    if json_mode:
        kwargs["format"] = "json"

    last_transport_error: Exception | None = None
    for attempt in range(2):
        try:
            # ``think`` is supported by newer ollama clients; degrade gracefully.
            try:
                resp = _client.chat(think=think, **kwargs)
            except TypeError:
                resp = _client.chat(**kwargs)
            break
        except ollama.ResponseError as exc:  # model not pulled, bad request, etc.
            raise BrainError(f"Ollama rejected the request ({name}): {exc}") from exc
        except (ConnectionError, httpx.TransportError) as exc:
            last_transport_error = exc
            if attempt == 0:
                time.sleep(2)
                continue
            raise BrainError(
                "Could not reach Ollama at "
                f"{settings.ollama_url}. Is it running?  (try: `ollama serve`) "
                f"Last error: {exc}"
            ) from exc
    else:  # defensive; the loop either breaks or raises
        raise BrainError(f"Ollama request failed: {last_transport_error}")

    content = resp.get("message", {}).get("content", "")
    if not content:
        raise BrainError(f"Empty response from model {name}: {resp}")
    return strip_thinking(content)


def stream(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    role: Role = "brain",
    temperature: float | None = None,
) -> Iterator[str]:
    """Yield response chunks for interactive display."""
    name = _resolve_model(model, role)
    try:
        for part in _client.chat(
            model=name,
            messages=messages,
            options=_options(temperature),
            stream=True,
        ):
            piece = part.get("message", {}).get("content", "")
            if piece:
                yield piece
    except ConnectionError as exc:
        raise BrainError(
            f"Could not reach Ollama at {settings.ollama_url}. Is it running?"
        ) from exc


def health() -> dict[str, Any]:
    """Return which configured models are actually pulled locally."""
    try:
        listed = _client.list().get("models", [])
    except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
        return {"ok": False, "error": str(exc), "models": []}
    available = {m.get("model", m.get("name", "")) for m in listed}
    roles = {
        "brain": settings.brain_model,
        "worker": settings.worker_model,
        "heavy": settings.heavy_model,
    }
    return {
        "ok": True,
        "available": sorted(available),
        "roles": {r: {"model": n, "pulled": n in available} for r, n in roles.items()},
    }


# --- Backwards-compatible shim for the Phase-0 loop --------------------------
def ask_model(messages: list[dict[str, Any]]) -> str:
    """Legacy entry point kept so existing code/tests keep working."""
    return chat(messages, role="worker")


if __name__ == "__main__":
    import json

    print(json.dumps(health(), indent=2))
    print(ask_model([{"role": "user", "content": "Reply with exactly: brain online"}]))
