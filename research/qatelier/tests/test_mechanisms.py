from __future__ import annotations

import numpy as np

from research.qatelier.mechanisms import (
    centered_kernel_alignment,
    effective_rank,
    finite_difference_gradient,
    gradient_summary,
    spectral_summary,
)


def test_kernel_alignment_and_effective_rank_are_deterministic():
    features = np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    kernel = features @ features.T
    target = np.outer(np.array([-1.0, 1.0, 1.0]), np.array([-1.0, 1.0, 1.0]))
    assert -1.0 <= centered_kernel_alignment(kernel, target) <= 1.0
    assert effective_rank(kernel) >= 1.0


def test_spectrum_and_gradient_diagnostics_have_explicit_shapes():
    values = np.sin(np.linspace(0, 2 * np.pi, 32))[:, None]
    spectrum = spectral_summary(values)
    assert spectrum["signal_length"] == 32
    gradient = finite_difference_gradient(lambda theta: float(np.sum(theta**2)), np.array([1.0, -2.0]))
    np.testing.assert_allclose(gradient, [2.0, -4.0], atol=1e-7)
    summary = gradient_summary(np.vstack([gradient, gradient * 2]))
    assert summary["parameter_count"] == 2
    assert summary["n_observations"] == 2
