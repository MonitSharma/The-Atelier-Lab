"""Deterministic, model-agnostic diagnostics for QAtelier mechanism screens."""

from __future__ import annotations

from collections.abc import Callable
import math
from typing import Any

import numpy as np


def _center(matrix: np.ndarray) -> np.ndarray:
    values = np.asarray(matrix, dtype=float)
    return values - values.mean(axis=0, keepdims=True) - values.mean(axis=1, keepdims=True) + values.mean()


def centered_kernel_alignment(kernel: np.ndarray, target: np.ndarray) -> float:
    """Return centered kernel-target alignment in [-1, 1] when non-degenerate."""

    left = _center(np.asarray(kernel, dtype=float))
    right = _center(np.asarray(target, dtype=float))
    if left.shape != right.shape or left.ndim != 2 or left.shape[0] != left.shape[1]:
        raise ValueError("kernel and target must be aligned square matrices")
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 0.0
    return float(np.sum(left * right) / denominator)


def effective_rank(matrix: np.ndarray, *, tolerance: float = 1e-12) -> float:
    """Return entropy effective rank from the non-negative singular spectrum."""

    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError("matrix must be a finite 2-D array")
    singular = np.linalg.svd(values, compute_uv=False)
    singular = singular[singular > tolerance]
    if singular.size == 0:
        return 0.0
    probabilities = singular / singular.sum()
    return float(np.exp(-np.sum(probabilities * np.log(probabilities))))


def spectral_summary(values: np.ndarray, *, axis: int = 0, remove_dc: bool = True) -> dict[str, Any]:
    """Summarize empirical Fourier mass along one feature axis."""

    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise ValueError("values must be a finite 2-D array")
    if axis not in (0, 1):
        raise ValueError("axis must be 0 or 1")
    signal = array.mean(axis=1 - axis)
    spectrum = np.abs(np.fft.rfft(signal)) ** 2
    if remove_dc and spectrum.size:
        spectrum[0] = 0.0
    total = float(spectrum.sum())
    probabilities = spectrum / total if total > 0 else spectrum
    entropy = float(-np.sum(probabilities[probabilities > 0] * np.log(probabilities[probabilities > 0]))) if total > 0 else 0.0
    return {
        "axis": axis,
        "signal_length": int(signal.size),
        "frequency_bins": int(spectrum.size),
        "spectral_mass": float(total),
        "spectral_entropy": entropy,
        "effective_frequency_count": float(np.exp(entropy)) if total > 0 else 0.0,
        "dominant_frequency_bin": int(np.argmax(spectrum)) if spectrum.size else None,
        "power": spectrum.tolist(),
    }


def finite_difference_gradient(
    objective: Callable[[np.ndarray], float], parameters: np.ndarray, *, epsilon: float = 1e-4
) -> np.ndarray:
    """Compute a central finite-difference gradient with explicit epsilon."""

    if epsilon <= 0 or not math.isfinite(epsilon):
        raise ValueError("epsilon must be positive and finite")
    values = np.asarray(parameters, dtype=float)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError("parameters must be a finite 1-D array")
    gradient = np.zeros_like(values)
    for index in range(values.size):
        plus = values.copy()
        minus = values.copy()
        plus[index] += epsilon
        minus[index] -= epsilon
        gradient[index] = (float(objective(plus)) - float(objective(minus))) / (2.0 * epsilon)
    return gradient


def gradient_summary(gradients: np.ndarray) -> dict[str, float | int]:
    """Summarize gradient norms across seeds or training checkpoints."""

    values = np.asarray(gradients, dtype=float)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError("gradients must be a finite 1-D or 2-D array")
    norms = np.linalg.norm(values, axis=1)
    variances = np.var(values, axis=0)
    return {
        "n_observations": int(values.shape[0]),
        "parameter_count": int(values.shape[1]),
        "norm_mean": float(norms.mean()),
        "norm_std": float(norms.std(ddof=1)) if norms.size > 1 else 0.0,
        "component_variance_mean": float(variances.mean()),
        "component_variance_max": float(variances.max()),
    }


__all__ = [
    "centered_kernel_alignment",
    "effective_rank",
    "finite_difference_gradient",
    "gradient_summary",
    "spectral_summary",
]
