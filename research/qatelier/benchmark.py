"""Deterministic synthetic data for interaction-order experiments.

The generator in this module is deliberately small and dependency-light.  It
creates binary classification problems whose score depends on an interaction
of a requested order.  An integer seed always uses a local
``numpy.random.Generator``; global NumPy random state is never read or changed.

Example
-------
>>> data = generate_interaction_order_data(128, 6, 3, family="rotated", seed=7)
>>> data.features.shape, data.labels.shape
((128, 6), (128,))
>>> data.metadata["interaction_order"]
3

The supported families are:

``polynomial``
    A deterministic sum of exact-degree polynomial monomials.
``fourier`` / ``trigonometric``
    A product of sinusoidal factors, one for each interacting coordinate.
``aligned``
    A single monomial on the first ``interaction_order`` feature axes.
``rotated``
    The aligned monomial expressed in a deterministic shared orthogonal basis.
``misaligned``
    A product of projections onto independently sampled dense directions.

Labels are encoded as integers ``0`` and ``1``.  They are assigned by the
median of the continuous score, so the two classes are exactly balanced for an
even number of samples and differ by at most one sample for an odd number.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterator, Mapping

import numpy as np


SUPPORTED_FAMILIES = ("polynomial", "fourier", "rotated", "aligned", "misaligned")
"""Canonical family names accepted by :func:`generate_interaction_order_data`."""

_FAMILY_ALIASES = {"trigonometric": "fourier"}
_MAX_POLYNOMIAL_TERMS = 12


@dataclass(frozen=True)
class BenchmarkDataset:
    """Features, binary labels, and provenance for one generated dataset.

    ``features`` has shape ``(n_samples, n_features)`` and ``labels`` has
    shape ``(n_samples,)``.  The object can also be unpacked as
    ``features, labels, metadata`` for lightweight experiment scripts.
    """

    features: np.ndarray
    labels: np.ndarray
    metadata: Mapping[str, Any]

    @property
    def X(self) -> np.ndarray:
        """Alias for :attr:`features`, useful in array-oriented experiments."""
        return self.features

    @property
    def y(self) -> np.ndarray:
        """Alias for :attr:`labels`, useful in array-oriented experiments."""
        return self.labels

    def __iter__(self) -> Iterator[Any]:
        """Yield ``features``, ``labels``, and ``metadata`` in that order."""
        yield self.features
        yield self.labels
        yield self.metadata


def _canonical_family(family: str) -> str:
    if not isinstance(family, str):
        raise TypeError("family must be a string")
    canonical = _FAMILY_ALIASES.get(family.strip().lower(), family.strip().lower())
    if canonical not in SUPPORTED_FAMILIES:
        choices = ", ".join(SUPPORTED_FAMILIES)
        raise ValueError(f"unknown family {family!r}; choose one of: {choices}")
    return canonical


def _validate_dimensions(n_samples: int, n_features: int, interaction_order: int) -> None:
    values = (
        ("n_samples", n_samples),
        ("n_features", n_features),
        ("interaction_order", interaction_order),
    )
    for name, value in values:
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise TypeError(f"{name} must be an integer")
        if value < 1:
            raise ValueError(f"{name} must be positive")
    if interaction_order > n_features:
        raise ValueError("interaction_order cannot exceed n_features")


def _orthogonal_matrix(rng: np.random.Generator, size: int) -> np.ndarray:
    """Return a deterministic orthogonal matrix with a fixed QR convention."""
    matrix = rng.standard_normal((size, size))
    q, r = np.linalg.qr(matrix)
    diagonal = np.sign(np.diag(r))
    diagonal[diagonal == 0] = 1.0
    return q * diagonal


def _product(values: np.ndarray) -> np.ndarray:
    """Multiply columns without changing the output shape for order one."""
    return np.multiply.reduce(values, axis=1)


def _balanced_labels(scores: np.ndarray) -> np.ndarray:
    """Convert scores to deterministic median-split labels."""
    labels = np.zeros(scores.shape[0], dtype=np.int8)
    ordering = np.argsort(scores, kind="mergesort")
    labels[ordering[scores.shape[0] // 2 :]] = 1
    return labels


def generate_interaction_order_data(
    n_samples: int,
    n_features: int,
    interaction_order: int,
    family: str = "polynomial",
    seed: int = 0,
) -> BenchmarkDataset:
    """Generate a deterministic binary interaction-order classification set.

    Parameters
    ----------
    n_samples:
        Number of rows to generate.  At least one row is required.
    n_features:
        Number of standard-normal input features.
    interaction_order:
        Positive interaction degree, no greater than ``n_features``.
    family:
        One of ``polynomial``, ``fourier`` (or ``trigonometric``), ``rotated``,
        ``aligned``, or ``misaligned``.  See the module documentation for the
        mathematical distinction between families.
    seed:
        Integer seed for a local ``numpy.random.PCG64`` generator.  Repeating
        all arguments, including this seed, returns identical arrays and
        metadata without affecting NumPy's global random state.

    Returns
    -------
    BenchmarkDataset
        A result with ``features``, ``labels``, and metadata containing at
        least ``family``, ``interaction_order``, ``n_samples``, ``n_features``,
        ``seed``, and ``class_counts``.
    """
    _validate_dimensions(n_samples, n_features, interaction_order)
    canonical_family = _canonical_family(family)
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError("seed must be an integer")

    rng = np.random.Generator(np.random.PCG64(int(seed)))
    features = rng.standard_normal((int(n_samples), int(n_features)))
    order = int(interaction_order)
    interaction_coordinates: tuple[int, ...] | None = None
    transform: np.ndarray | None = None

    if canonical_family == "polynomial":
        # Use a deterministic subset when the full degree-order expansion is
        # large; every retained term still has exactly the requested degree.
        terms = tuple(combinations(range(n_features), order))
        if len(terms) > _MAX_POLYNOMIAL_TERMS:
            positions = np.linspace(
                0, len(terms) - 1, _MAX_POLYNOMIAL_TERMS, dtype=int
            )
            terms = tuple(terms[position] for position in positions)
        scores = np.zeros(n_samples, dtype=np.float64)
        coefficient_scale = 1.0 / np.sqrt(len(terms))
        for term_index, term in enumerate(terms):
            term_score = _product(features[:, term])
            coefficient = coefficient_scale if term_index % 2 == 0 else -coefficient_scale
            scores += coefficient * term_score
        interaction_coordinates = tuple(sorted({index for term in terms for index in term}))
        score_description = "deterministic sum of exact-degree monomials"
    elif canonical_family == "fourier":
        scores = _product(np.sin(np.pi * features[:, :order] / 2.0))
        interaction_coordinates = tuple(range(order))
        score_description = "product of sinusoidal factors"
    elif canonical_family == "aligned":
        scores = _product(features[:, :order])
        interaction_coordinates = tuple(range(order))
        score_description = "single axis-aligned monomial"
    elif canonical_family == "rotated":
        transform = _orthogonal_matrix(rng, n_features)
        latent_features = features @ transform.T
        scores = _product(latent_features[:, :order])
        score_description = "single monomial in a shared orthogonal basis"
    else:  # misaligned
        directions = rng.standard_normal((n_features, order))
        directions /= np.linalg.norm(directions, axis=0, keepdims=True)
        projections = features @ directions
        scores = _product(projections)
        score_description = "product of projections onto dense independent directions"

    labels = _balanced_labels(scores)
    metadata: dict[str, Any] = {
        "family": canonical_family,
        "interaction_order": order,
        "n_samples": int(n_samples),
        "n_features": int(n_features),
        "seed": int(seed),
        "label_encoding": "0=lower score half, 1=upper score half",
        "class_counts": {
            "0": int(np.count_nonzero(labels == 0)),
            "1": int(np.count_nonzero(labels == 1)),
        },
        "score_definition": score_description,
    }
    if interaction_coordinates is not None:
        metadata["interaction_coordinates"] = interaction_coordinates
    if transform is not None:
        metadata["rotation_is_orthogonal"] = True

    return BenchmarkDataset(features=features, labels=labels, metadata=metadata)


__all__ = [
    "BenchmarkDataset",
    "SUPPORTED_FAMILIES",
    "generate_interaction_order_data",
]
