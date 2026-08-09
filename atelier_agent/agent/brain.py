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
from collections.abc import Callable, Iterator
from typing import Any

from atelier.config import settings
from models.registry import provider_for, specs_from_settings
from models.types import ModelSpec, Role

_SPECS = specs_from_settings(settings)
if "heavy" not in _SPECS:
    _SPECS["heavy"] = ModelSpec("heavy", settings.model_provider, settings.heavy_model, "heavy")
_provider = provider_for(settings)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class BrainError(RuntimeError):
    """Raised when the local model cannot be reached or returns nothing usable."""


def _resolve_model(model: str | None, role: Role) -> str:
    if model:
        return model
    return _SPECS.get(role, _SPECS["brain"]).model_id


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
    json_schema: dict[str, Any] | None = None,
    think: bool = False,
    on_result: Callable[[Any], None] | None = None,
) -> str:
    """Send a conversation and return the assistant's text.

    ``role`` selects the model size when ``model`` is not given explicitly.
    ``json_mode`` constrains the model to emit valid JSON (used for tool calls).
    ``think`` toggles qwen3 reasoning traces; off by default for clean output.
    """
    name = _resolve_model(model, role)
    try:
        spec = _SPECS.get(role, _SPECS["brain"])
        if model:
            spec = ModelSpec(spec.name, spec.provider, model, spec.role, spec.quantization, spec.max_context, spec.supports_tools, spec.supports_json)
        kwargs: dict[str, Any] = {
            "temperature": settings.temperature if temperature is None else temperature,
            "json_mode": json_mode,
            "think": think,
        }
        if json_schema is not None:
            kwargs["json_schema"] = json_schema
        result = _provider.generate(messages, spec, **kwargs)
        if on_result is not None:
            on_result(result)
        return strip_thinking(result.text)
    except Exception as exc:  # provider-specific errors become stable public errors
        raise BrainError(f"Local provider request failed for {name}: {exc}") from exc


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
        spec = _SPECS.get(role, _SPECS["brain"])
        if model:
            spec = ModelSpec(spec.name, spec.provider, model, spec.role, spec.quantization, spec.max_context, spec.supports_tools, spec.supports_json)
        yield from _provider.stream(messages, spec, temperature=settings.temperature if temperature is None else temperature)
    except Exception as exc:
        raise BrainError(f"Local provider stream failed for {name}: {exc}") from exc


def health() -> dict[str, Any]:
    """Return which configured models are actually pulled locally."""
    try:
        import ollama
        listed = ollama.Client(host=settings.ollama_url).list().get("models", [])
    except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
        return {"ok": False, "error": str(exc), "models": []}
    available = {m.get("model", m.get("name", "")) for m in listed}
    configured_roles = {
        "brain": settings.brain_model,
        "coder": settings.coder_model,
        "worker": settings.worker_model,
        "heavy": settings.heavy_model,
        "expert": settings.expert_model,
        "router": settings.router_model,
    }
    roles = {
        role: {"model": model, "configured": bool(model), "pulled": bool(model) and model in available}
        for role, model in configured_roles.items()
    }
    return {
        "ok": True,
        "available": sorted(available),
        "roles": roles,
    }


# --- Backwards-compatible shim for the Phase-0 loop --------------------------
def ask_model(messages: list[dict[str, Any]]) -> str:
    """Legacy entry point kept so existing code/tests keep working."""
    return chat(messages, role="worker")


if __name__ == "__main__":
    import json

    print(json.dumps(health(), indent=2))
    print(ask_model([{"role": "user", "content": "Reply with exactly: brain online"}]))
