"""MLX provider scaffold.

The adapter intentionally does not download or load a model. Configure a future
MLX implementation behind this interface when a local checkpoint is available.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .types import GenerationResult, ModelSpec


class MLXProvider:
    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path

    def _unconfigured(self) -> None:
        raise RuntimeError("MLX provider is a scaffold: set ATELIER_MLX_MODEL_PATH to a local model implementation before use")

    def generate(self, messages: list[dict[str, Any]], spec: ModelSpec, *, temperature: float, json_mode: bool = False, think: bool = False) -> GenerationResult:
        self._unconfigured()

    def stream(self, messages: list[dict[str, Any]], spec: ModelSpec, *, temperature: float) -> Iterator[str]:
        self._unconfigured()
        yield ""  # pragma: no cover
