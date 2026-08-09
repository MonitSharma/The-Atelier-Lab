"""Configuration-driven model role registry."""

from __future__ import annotations

from .base import ModelProvider
from .mlx_provider import MLXProvider
from .ollama_provider import OllamaProvider
from .types import ModelSpec, Role


def specs_from_settings(settings) -> dict[Role, ModelSpec]:
    """Build role specs without naming a future or unreleased model."""
    configured = {
        "worker": settings.worker_model,
        "brain": settings.brain_model,
        "expert": settings.expert_model,
        "router": settings.router_model,
    }
    return {role: ModelSpec(role, settings.model_provider, model_id, role) for role, model_id in configured.items()}


def provider_for(settings) -> ModelProvider:
    if settings.model_provider == "mlx":
        return MLXProvider(settings.mlx_model_path)
    return OllamaProvider(settings.ollama_url)
