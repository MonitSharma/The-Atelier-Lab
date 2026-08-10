"""Deterministic controlled interaction-order benchmark data.

The benchmark has two deliberately separate operations:

``make_interaction_problem``
    Constructs the latent target function once.  Its interaction directions,
    rotation, Fourier frequencies, polynomial terms, and decision threshold
    are all fixed by ``problem_seed`` and are independent of any split.

``InteractionProblem.sample``
    Draws fresh observations from an existing problem using a split-specific
    ``seed``.  Train, validation, and test data can therefore share exactly
    the same target function without sharing observations or recalibrating the
    threshold.

The supported target families are aligned, rotated, misaligned, Fourier (with
``trigonometric`` as a compatibility alias), and polynomial.  Noise is applied
only during sampling: observation noise perturbs the observed features and
label noise independently flips labels.  Neither operation changes the
latent target function.

The legacy :func:`generate_interaction_order_data` wrapper remains available
for small scripts.  New experiments should construct one problem and call
``problem.sample`` once per split.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
from typing import Any

import numpy as np

SUPPORTED_FAMILIES = ("polynomial", "fourier", "aligned", "rotated", "misaligned")
"""Canonical family names accepted by :func:`make_interaction_problem`."""

_FAMILY_ALIASES = {"trigonometric": "fourier"}
_MAX_POLYNOMIAL_TERMS = 12


def _canonical_family(family: str) -> str:
    if not isinstance(family, str):
        raise TypeError("family must be a string")
    canonical = _FAMILY_ALIASES.get(family.strip().lower(), family.strip().lower())
    if canonical not in SUPPORTED_FAMILIES:
        choices = ", ".join(SUPPORTED_FAMILIES)
        raise ValueError(f"unknown family {family!r}; choose one of: {choices}")
    return canonical


def _validate_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    return int(value)


def _validate_dimensions(n_features: int, interaction_order: int) -> tuple[int, int]:
    n_features = _validate_integer("n_features", n_features)
    interaction_order = _validate_integer("interaction_order", interaction_order)
    if n_features < 1:
        raise ValueError("n_features must be positive")
    if interaction_order < 1:
        raise ValueError("interaction_order must be positive")
    if interaction_order > n_features:
        raise ValueError("interaction_order cannot exceed n_features")
    return n_features, interaction_order


def _resolve_order(order: int | None, interaction_order: int | None) -> int:
    if order is None and interaction_order is None:
        raise TypeError("one of order or interaction_order is required")
    if order is not None and interaction_order is not None and order != interaction_order:
        raise ValueError("order and interaction_order must agree when both are provided")
    return _validate_integer("order", order if order is not None else interaction_order)  # type: ignore[arg-type]


def _validate_noise(name: str, value: float, *, upper_bound: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not np.isfinite(result) or result < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    if upper_bound is not None and result > upper_bound:
        raise ValueError(f"{name} must be at most {upper_bound}")
    return result


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


def _readonly(array: np.ndarray | None) -> np.ndarray | None:
    if array is None:
        return None
    result = np.array(array, dtype=np.float64, copy=True)
    result.setflags(write=False)
    return result


def _hash_target(
    *,
    family: str,
    n_features: int,
    interaction_order: int,
    threshold: float,
    rotation: np.ndarray | None,
    directions: np.ndarray | None,
    polynomial_terms: tuple[tuple[int, ...], ...],
    polynomial_coefficients: np.ndarray | None,
    fourier_frequencies: np.ndarray | None,
) -> str:
    digest = sha256()
    digest.update(
        repr(
            (
                family,
                n_features,
                interaction_order,
                float(threshold),
                polynomial_terms,
            )
        ).encode("utf-8")
    )
    for name, array in (
        ("rotation", rotation),
        ("directions", directions),
        ("polynomial_coefficients", polynomial_coefficients),
        ("fourier_frequencies", fourier_frequencies),
    ):
        digest.update(name.encode("utf-8"))
        if array is None:
            digest.update(b"<none>")
        else:
            contiguous = np.ascontiguousarray(array)
            digest.update(str(contiguous.dtype).encode("utf-8"))
            digest.update(repr(contiguous.shape).encode("utf-8"))
            digest.update(contiguous.tobytes())
    return digest.hexdigest()


def _hash_sample(features: np.ndarray, labels: np.ndarray) -> str:
    digest = sha256()
    for array in (features, labels):
        contiguous = np.ascontiguousarray(array)
        digest.update(str(contiguous.dtype).encode("utf-8"))
        digest.update(repr(contiguous.shape).encode("utf-8"))
        digest.update(contiguous.tobytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class BenchmarkDataset:
    """Features, binary labels, and provenance for one generated split."""

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


@dataclass(frozen=True)
class InteractionProblem:
    """A frozen latent interaction function that can generate many splits.

    The public scalar fields and target arrays describe the problem, not a
    particular sample.  ``sample`` uses a fresh local RNG for every split and
    never mutates this object.  Target arrays are read-only to prevent an
    accidental post-construction change from invalidating the fingerprint.
    """

    n_features: int
    interaction_order: int
    family: str
    problem_seed: int
    threshold: float
    threshold_source: str
    observation_noise_std: float
    label_noise: float
    rotation: np.ndarray | None
    directions: np.ndarray | None
    polynomial_terms: tuple[tuple[int, ...], ...]
    polynomial_coefficients: np.ndarray | None
    fourier_frequencies: np.ndarray | None
    target_fingerprint: str

    @property
    def order(self) -> int:
        """Alias for the interaction order used by the constructor contract."""
        return self.interaction_order

    @property
    def target_definition(self) -> Mapping[str, Any]:
        """Return a compact, JSON-friendly description of the latent target."""
        definition: dict[str, Any] = {
            "family": self.family,
            "n_features": self.n_features,
            "interaction_order": self.interaction_order,
            "threshold": self.threshold,
            "threshold_source": self.threshold_source,
            "target_fingerprint": self.target_fingerprint,
        }
        if self.polynomial_terms:
            definition["polynomial_terms"] = self.polynomial_terms
        if self.fourier_frequencies is not None:
            definition["fourier_frequencies"] = tuple(
                int(value) for value in self.fourier_frequencies
            )
        if self.rotation is not None:
            definition["rotation_is_orthogonal"] = True
        if self.directions is not None:
            definition["direction_count"] = int(self.directions.shape[1])
        if self.interaction_coordinates is not None:
            definition["interaction_coordinates"] = self.interaction_coordinates
        return definition

    @property
    def interaction_coordinates(self) -> tuple[int, ...] | None:
        """Coordinates involved directly, or ``None`` for dense directions."""
        if self.family in {"aligned", "fourier", "rotated"}:
            return tuple(range(self.interaction_order))
        if self.family == "polynomial":
            return tuple(
                sorted({index for term in self.polynomial_terms for index in term})
            )
        return None

    def _latent_coordinates(self, features: np.ndarray) -> np.ndarray:
        if self.family == "rotated":
            assert self.rotation is not None
            return features @ self.rotation.T
        if self.family == "misaligned":
            assert self.directions is not None
            return features @ self.directions
        return features[:, : self.interaction_order]

    def score(self, features: np.ndarray) -> np.ndarray:
        """Evaluate the fixed, noiseless target function on feature rows."""
        values = np.asarray(features, dtype=np.float64)
        if values.ndim != 2:
            raise ValueError("features must be a two-dimensional array")
        if values.shape[1] != self.n_features:
            raise ValueError(
                f"features must have {self.n_features} columns; got {values.shape[1]}"
            )

        coordinates = self._latent_coordinates(values)
        if self.family == "polynomial":
            assert self.polynomial_coefficients is not None
            scores = np.zeros(values.shape[0], dtype=np.float64)
            for coefficient, term in zip(self.polynomial_coefficients, self.polynomial_terms):
                scores += float(coefficient) * _product(values[:, term])
            return scores
        if self.family == "fourier":
            assert self.fourier_frequencies is not None
            factors = np.sin(np.pi * coordinates * self.fourier_frequencies / 2.0)
            return _product(factors)
        return _product(coordinates)

    def target_function(self, features: np.ndarray) -> np.ndarray:
        """Alias for :meth:`score` for callers using target-function terminology."""
        return self.score(features)

    def diagnostics(
        self,
        features: np.ndarray | None = None,
        labels: np.ndarray | None = None,
        *,
        scores: np.ndarray | None = None,
    ) -> Mapping[str, Any]:
        """Return analytical and, when data are supplied, empirical diagnostics.

        The analytical portion is split-independent.  The empirical portion
        is computed from the supplied sample and is intentionally reported as
        diagnostics rather than used to set the decision threshold.
        """
        analytical: dict[str, Any] = {
            "family": self.family,
            "interaction_order": self.interaction_order,
            "n_features": self.n_features,
            "threshold": self.threshold,
            "threshold_source": self.threshold_source,
            "target_terms": len(self.polynomial_terms) if self.family == "polynomial" else 1,
            "feature_distribution": "standard_normal",
        }
        if self.family == "fourier":
            analytical["frequency_count"] = self.interaction_order
        if self.family == "rotated":
            analytical["rotation_is_orthogonal"] = True
        if features is None:
            return {"analytical": analytical}

        values = np.asarray(features, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != self.n_features:
            raise ValueError("features have the wrong shape for this problem")
        if scores is None:
            scores = self.score(values)
        score_values = np.asarray(scores, dtype=np.float64)
        if score_values.shape != (values.shape[0],):
            raise ValueError("scores must have one value per feature row")

        margins = score_values - self.threshold
        target_positive_rate = float(np.mean(margins >= 0.0))
        empirical: dict[str, Any] = {
            "n_samples": int(values.shape[0]),
            "positive_rate": target_positive_rate,
            "target_positive_rate": target_positive_rate,
            "class_balance_gap": abs(target_positive_rate - 0.5),
            "score_mean": float(np.mean(score_values)),
            "score_std": float(np.std(score_values)),
            "score_min": float(np.min(score_values)),
            "score_max": float(np.max(score_values)),
            "score_quantiles": {
                "q05": float(np.quantile(score_values, 0.05)),
                "q50": float(np.quantile(score_values, 0.50)),
                "q95": float(np.quantile(score_values, 0.95)),
            },
            "margin_mean": float(np.mean(np.abs(margins))),
            "margin_std": float(np.std(margins)),
            "near_threshold_fraction": float(np.mean(np.abs(margins) <= 0.1)),
            "feature_mean_l2": float(np.linalg.norm(np.mean(values, axis=0))),
            "feature_std_mean": float(np.mean(np.std(values, axis=0))),
        }
        if labels is not None:
            label_values = np.asarray(labels)
            if label_values.shape != (values.shape[0],):
                raise ValueError("labels must have one value per feature row")
            counts = np.bincount(label_values.astype(np.int8), minlength=2)
            empirical["class_counts"] = {"0": int(counts[0]), "1": int(counts[1])}
            observed_positive_rate = float(np.mean(label_values == 1))
            empirical["positive_rate"] = observed_positive_rate
            empirical["class_balance_gap"] = abs(observed_positive_rate - 0.5)
        return {"analytical": analytical, "empirical": empirical}

    def sample(
        self,
        n: int,
        seed: int = 0,
        *,
        observation_noise_std: float | None = None,
        label_noise: float | None = None,
    ) -> BenchmarkDataset:
        """Sample an independent split from this frozen problem.

        A split's labels are generated from the latent, clean features and the
        problem's fixed threshold.  Observation noise affects only returned
        features; label noise flips labels after thresholding.  Both noise
        processes are controlled by the split seed and are therefore
        reproducible without coupling the split to another split.
        """
        n = _validate_integer("n", n)
        if n < 1:
            raise ValueError("n must be positive")
        seed = _validate_integer("seed", seed)
        effective_observation_noise = (
            self.observation_noise_std
            if observation_noise_std is None
            else _validate_noise("observation_noise_std", observation_noise_std)
        )
        effective_label_noise = (
            self.label_noise
            if label_noise is None
            else _validate_noise("label_noise", label_noise, upper_bound=1.0)
        )
        rng = np.random.Generator(np.random.PCG64(seed))
        latent_features = rng.standard_normal((n, self.n_features))
        scores = self.score(latent_features)
        labels = (scores >= self.threshold).astype(np.int8)
        if effective_label_noise:
            flips = rng.random(n) < effective_label_noise
            labels[flips] = 1 - labels[flips]

        features = latent_features.copy()
        if effective_observation_noise:
            features += rng.normal(
                loc=0.0,
                scale=effective_observation_noise,
                size=features.shape,
            )

        diagnostics = self.diagnostics(features, labels, scores=scores)
        counts = np.bincount(labels, minlength=2)
        metadata: dict[str, Any] = {
            "family": self.family,
            "interaction_order": self.interaction_order,
            "n_samples": n,
            "n_features": self.n_features,
            "problem_seed": self.problem_seed,
            "sample_seed": seed,
            # ``seed`` is retained for compatibility with the original helper.
            "seed": seed,
            "target_fingerprint": self.target_fingerprint,
            "target_definition": self.target_definition,
            "interaction_coordinates": self.interaction_coordinates,
            "threshold": self.threshold,
            "threshold_source": self.threshold_source,
            "label_encoding": "1=score >= fixed threshold; 0=otherwise",
            "class_counts": {"0": int(counts[0]), "1": int(counts[1])},
            "noise": {
                "observation_std": effective_observation_noise,
                "label_flip_probability": effective_label_noise,
            },
            "diagnostics": diagnostics,
            "sample_fingerprint": _hash_sample(features, labels),
        }
        return BenchmarkDataset(features=features, labels=labels, metadata=metadata)


def make_interaction_problem(
    n_features: int,
    order: int | None = None,
    family: str = "polynomial",
    problem_seed: int = 0,
    *,
    interaction_order: int | None = None,
    threshold: float | None = None,
    observation_noise_std: float = 0.0,
    label_noise: float = 0.0,
) -> InteractionProblem:
    """Construct a reusable latent interaction problem.

    Parameters
    ----------
    n_features:
        Number of standard-normal input features.
    order / interaction_order:
        Positive interaction order.  ``interaction_order`` is a compatibility
        keyword; new code should use the shorter ``order`` spelling.
    family:
        ``aligned``, ``rotated``, ``misaligned``, ``fourier`` (or
        ``trigonometric``), or ``polynomial``.
    problem_seed:
        Seed for target construction only.  It never seeds split sampling.
    threshold:
        Fixed decision boundary.  If omitted, the natural zero boundary is
        used for these symmetric target families; it is never estimated from
        a validation or test split.
    observation_noise_std:
        Standard deviation of independent additive noise on observed features.
    label_noise:
        Probability of independently flipping each thresholded label.
    """
    order = _resolve_order(order, interaction_order)
    n_features, order = _validate_dimensions(n_features, order)
    family = _canonical_family(family)
    problem_seed = _validate_integer("problem_seed", problem_seed)
    observation_noise_std = _validate_noise("observation_noise_std", observation_noise_std)
    label_noise = _validate_noise("label_noise", label_noise, upper_bound=1.0)

    if threshold is None:
        threshold_value = 0.0
        threshold_source = "natural_zero_for_symmetric_target"
    else:
        if isinstance(threshold, bool) or not isinstance(
            threshold, (int, float, np.integer, np.floating)
        ):
            raise TypeError("threshold must be a real number or None")
        threshold_value = float(threshold)
        if not np.isfinite(threshold_value):
            raise ValueError("threshold must be finite")
        threshold_source = "declared_before_sampling"

    rng = np.random.Generator(np.random.PCG64(problem_seed))
    rotation: np.ndarray | None = None
    directions: np.ndarray | None = None
    polynomial_terms: tuple[tuple[int, ...], ...] = ()
    polynomial_coefficients: np.ndarray | None = None
    fourier_frequencies: np.ndarray | None = None

    if family == "polynomial":
        all_terms = tuple(combinations(range(n_features), order))
        if len(all_terms) > _MAX_POLYNOMIAL_TERMS:
            positions = np.linspace(0, len(all_terms) - 1, _MAX_POLYNOMIAL_TERMS, dtype=int)
            polynomial_terms = tuple(all_terms[position] for position in positions)
        else:
            polynomial_terms = all_terms
        polynomial_coefficients = rng.standard_normal(len(polynomial_terms))
        polynomial_coefficients /= np.linalg.norm(polynomial_coefficients)
    elif family == "rotated":
        rotation = _orthogonal_matrix(rng, n_features)
    elif family == "misaligned":
        directions = rng.standard_normal((n_features, order))
        directions /= np.linalg.norm(directions, axis=0, keepdims=True)
    elif family == "fourier":
        fourier_frequencies = rng.integers(1, 4, size=order).astype(np.float64)

    rotation = _readonly(rotation)
    directions = _readonly(directions)
    polynomial_coefficients = _readonly(polynomial_coefficients)
    fourier_frequencies = _readonly(fourier_frequencies)
    target_fingerprint = _hash_target(
        family=family,
        n_features=n_features,
        interaction_order=order,
        threshold=threshold_value,
        rotation=rotation,
        directions=directions,
        polynomial_terms=polynomial_terms,
        polynomial_coefficients=polynomial_coefficients,
        fourier_frequencies=fourier_frequencies,
    )
    return InteractionProblem(
        n_features=n_features,
        interaction_order=order,
        family=family,
        problem_seed=problem_seed,
        threshold=threshold_value,
        threshold_source=threshold_source,
        observation_noise_std=observation_noise_std,
        label_noise=label_noise,
        rotation=rotation,
        directions=directions,
        polynomial_terms=polynomial_terms,
        polynomial_coefficients=polynomial_coefficients,
        fourier_frequencies=fourier_frequencies,
        target_fingerprint=target_fingerprint,
    )


def generate_interaction_order_data(
    n_samples: int,
    n_features: int,
    interaction_order: int,
    family: str = "polynomial",
    seed: int = 0,
    *,
    threshold: float | None = None,
    observation_noise_std: float = 0.0,
    label_noise: float = 0.0,
) -> BenchmarkDataset:
    """Compatibility wrapper for one-shot generation.

    This helper constructs a problem using ``seed`` and samples it with the
    same seed.  It is deterministic, but it cannot express shared train/
    validation/test targets; use :func:`make_interaction_problem` for that
    protocol.
    """
    problem = make_interaction_problem(
        n_features=n_features,
        order=interaction_order,
        family=family,
        problem_seed=seed,
        threshold=threshold,
        observation_noise_std=observation_noise_std,
        label_noise=label_noise,
    )
    return problem.sample(n_samples, seed=seed)


__all__ = [
    "SUPPORTED_FAMILIES",
    "BenchmarkDataset",
    "InteractionProblem",
    "generate_interaction_order_data",
    "make_interaction_problem",
]
