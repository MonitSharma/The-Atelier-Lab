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

    def generate(self, messages: list[dict[str, Any]], spec: ModelSpec, *, temperature: float, json_mode: bool = False, think: bool = False) -> GenerationResult:
        kwargs: dict[str, Any] = {"model": spec.model_id, "messages": messages, "options": {"temperature": temperature}, "stream": False}
        if json_mode:
            kwargs["format"] = "json"
        started = time.perf_counter()
        try:
            response = self.client.chat(think=think, **kwargs)
        except TypeError:
            response = self.client.chat(**kwargs)
        content = response.get("message", {}).get("content", "")
        if not content:
            raise RuntimeError(f"Ollama returned an empty response for {spec.model_id}")
        return GenerationResult(text=content, model_name=spec.model_id, total_latency_s=time.perf_counter() - started)

    def stream(self, messages: list[dict[str, Any]], spec: ModelSpec, *, temperature: float) -> Iterator[str]:
        for part in self.client.chat(model=spec.model_id, messages=messages, options={"temperature": temperature}, stream=True):
            piece = part.get("message", {}).get("content", "")
            if piece:
                yield piece
