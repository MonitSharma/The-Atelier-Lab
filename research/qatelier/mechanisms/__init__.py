"""Diagnostics for QAtelier mechanism and trainability analyses."""

from .diagnostics import (
    centered_kernel_alignment,
    effective_rank,
    finite_difference_gradient,
    gradient_summary,
    spectral_summary,
)

__all__ = [
    "centered_kernel_alignment",
    "effective_rank",
    "finite_difference_gradient",
    "gradient_summary",
    "spectral_summary",
]
