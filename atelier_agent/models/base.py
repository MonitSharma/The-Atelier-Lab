"""Protocol shared by local model providers."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol

from .types import GenerationResult, ModelSpec


class ModelProvider(Protocol):
    def generate(self, messages: list[dict[str, Any]], spec: ModelSpec, *, temperature: float, json_mode: bool = False, think: bool = False) -> GenerationResult: ...

    def stream(self, messages: list[dict[str, Any]], spec: ModelSpec, *, temperature: float) -> Iterator[str]: ...
