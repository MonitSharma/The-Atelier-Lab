"""Provider-neutral model descriptions and results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Role = Literal["worker", "brain", "expert", "router", "heavy"]


@dataclass(frozen=True)
class ModelSpec:
    name: str
    provider: str
    model_id: str
    role: Role
    quantization: str | None = None
    max_context: int | None = None
    supports_tools: bool = False
    supports_json: bool = False


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model_name: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    time_to_first_token_s: float | None = None
    total_latency_s: float | None = None
    structured_output_valid: bool | None = None
