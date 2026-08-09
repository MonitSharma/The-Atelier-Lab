"""Ollama adapter; imports the optional client only when used."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from .types import GenerationResult, ModelSpec


class OllamaProvider:
    def __init__(self, url: str) -> None:
        import ollama

        self._ollama = ollama
        self.client = ollama.Client(host=url)

    def generate(self, messages: list[dict[str, Any]], spec: ModelSpec, *, temperature: float, json_mode: bool = False, json_schema: dict[str, Any] | None = None, think: bool = False) -> GenerationResult:
        kwargs: dict[str, Any] = {"model": spec.model_id, "messages": messages, "options": {"temperature": temperature}, "stream": False}
        if json_schema is not None:
            kwargs["format"] = json_schema
        elif json_mode:
            kwargs["format"] = "json"
        started = time.perf_counter()
        try:
            response = self.client.chat(think=think, **kwargs)
        except TypeError:
            response = self.client.chat(**kwargs)
        content = response.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError(f"Ollama returned an empty response for {spec.model_id}")
        def seconds(key: str) -> float | None:
            value = response.get(key)
            return float(value) / 1_000_000_000 if isinstance(value, (int, float)) else None

        return GenerationResult(
            text=content,
            model_name=spec.model_id,
            prompt_tokens=response.get("prompt_eval_count"),
            completion_tokens=response.get("eval_count"),
            total_latency_s=time.perf_counter() - started,
            load_duration_s=seconds("load_duration"),
            prompt_eval_duration_s=seconds("prompt_eval_duration"),
            completion_eval_duration_s=seconds("eval_duration"),
        )

    def stream(self, messages: list[dict[str, Any]], spec: ModelSpec, *, temperature: float) -> Iterator[str]:
        for part in self.client.chat(model=spec.model_id, messages=messages, options={"temperature": temperature}, stream=True):
            piece = part.get("message", {}).get("content", "")
            if piece:
                yield piece
