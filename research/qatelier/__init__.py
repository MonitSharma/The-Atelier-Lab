"""QAtelier: isolated quantum-adapter research utilities.

This package is intentionally separate from the production Atelier runtime.
The public surface starts with deterministic experiment manifests so every
benchmark result can be tied to an exact configuration and code version.
"""

from .manifest import ExperimentManifest, make_result_envelope

__all__ = ["ExperimentManifest", "make_result_envelope"]
