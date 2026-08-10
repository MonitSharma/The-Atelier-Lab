"""Executable, deterministic classical controls for QAtelier.

All controls consume one caller-supplied, already-compressed feature matrix.
The module does not fit encoders or compressors.  Each fitted model retains a
representation identity, split identity, feature-map seed, training hashes,
and capacity group so comparisons can be audited later.

Scikit-learn and PyTorch are optional and imported only when a selected model
needs them.  RBF/polynomial SVMs are deliberately labelled strong references;
their kernel capacity is not falsely equated with a trainable parameter count.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from time import perf_counter
from typing import Any

import numpy as np


class ClassicalDependencyError(ImportError):
    """Raised when a selected control needs an absent optional backend."""


OptionalDependencyError = ClassicalDependencyError

MODEL_NAMES = (
    "logistic",
    "linear_svm",
    "rbf_svm",
    "polynomial_svm",
    "random_fourier",
    "mlp",
    "low_rank_bilinear",
    "finite_rbf",
    "mps",
    "spectrum_matched",
)


def _require_sklearn() -> dict[str, Any]:
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.svm import LinearSVC, SVC
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ClassicalDependencyError(
            "these controls require scikit-learn; install the QAtelier scientific extra"
        ) from exc
    return {"logistic": LogisticRegression, "linear_svm": LinearSVC, "svc": SVC}


def _require_torch() -> Any:
    try:
        import torch
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ClassicalDependencyError(
            "the MPS control requires PyTorch; install the optional tensor backend"
        ) from exc
    return torch


def _json_ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(v) for v in value]
    return value


def _digest(value: Any) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    header = f"{array.dtype.str}:{array.shape}".encode()
    return hashlib.sha256(header + b"\0" + array.tobytes()).hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class RepresentationMetadata:
    """Identity of the shared frozen representation passed to each head."""

    representation_id: str = "unlabelled_representation"
    dimension: int = 0
    compressor_id: str | None = None
    compressor_hash: str | None = None
    split_id: str | None = None
    normalization: str | None = None
    feature_map_seed: int | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if not self.representation_id or self.dimension < 0:
            raise ValueError(
                "representation_id must be non-empty and dimension non-negative"
            )
        if self.feature_map_seed is not None and self.feature_map_seed < 0:
            raise ValueError("feature_map_seed must be non-negative")

    @classmethod
    def from_value(cls, value: Any, dimension: int) -> "RepresentationMetadata":
        if value is None:
            return cls(dimension=dimension)
        if isinstance(value, cls):
            if value.dimension not in (0, dimension):
                raise ValueError("representation dimension does not match X")
            return (
                cls(**{**asdict(value), "dimension": dimension})
                if value.dimension == 0
                else value
            )
        if isinstance(value, Mapping):
            payload = dict(value)
            payload.setdefault("dimension", dimension)
            return cls(**payload)
        raise TypeError("representation must be metadata, a mapping, or None")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        return _json_digest(self.to_dict())


@dataclass(frozen=True)
class SpectrumSpec:
    """Explicit Fourier support supplied by a quantum diagnostic."""

    frequencies: np.ndarray
    source: str = "external_quantum_diagnostic"
    spectrum_id: str = "provided_spectrum"
    seed: int | None = None

    def __post_init__(self) -> None:
        frequencies = np.asarray(self.frequencies, dtype=float)
        if frequencies.ndim == 1:
            frequencies = frequencies.reshape(1, -1)
        if (
            frequencies.ndim != 2
            or not frequencies.size
            or not np.all(np.isfinite(frequencies))
        ):
            raise ValueError("frequencies must be a finite non-empty 2D array")
        object.__setattr__(self, "frequencies", np.ascontiguousarray(frequencies))

    @classmethod
    def from_value(cls, value: Any) -> "SpectrumSpec":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            if "frequencies" not in value:
                raise ValueError("spectrum mapping must contain frequencies")
            return cls(
                value["frequencies"],
                str(value.get("source", cls.source)),
                str(value.get("spectrum_id", cls.spectrum_id)),
                value.get("seed"),
            )
        return cls(value)

    @property
    def fingerprint(self) -> str:
        return _json_digest(
            {
                "hash": _digest(self.frequencies),
                "source": self.source,
                "spectrum_id": self.spectrum_id,
            }
        )

    def to_dict(self, include_values: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            "source": self.source,
            "spectrum_id": self.spectrum_id,
            "seed": self.seed,
            "shape": list(self.frequencies.shape),
            "frequencies_hash": _digest(self.frequencies),
            "fingerprint": self.fingerprint,
        }
        if include_values:
            result["frequencies"] = self.frequencies.tolist()
        return result


def _validate_xy(X: Any, y: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features = np.asarray(X, dtype=float)
    labels = np.asarray(y)
    if features.ndim != 2 or not features.size or not np.all(np.isfinite(features)):
        raise ValueError("X must be a finite, non-empty 2D array")
    if labels.ndim != 1 or labels.shape[0] != features.shape[0]:
        raise ValueError("y must be a 1D array aligned with X")
    classes, encoded = np.unique(labels, return_inverse=True)
    if classes.size < 2:
        raise ValueError("classification controls require at least two classes")
    return features, labels, encoded.astype(np.int64)


def _softmax(scores: np.ndarray) -> np.ndarray:
    shifted = scores - scores.max(axis=1, keepdims=True)
    exp = np.exp(np.clip(shifted, -745, 80))
    return exp / exp.sum(axis=1, keepdims=True)


def _head_options(config: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "C",
        "class_weight",
        "fit_intercept",
        "max_iter",
        "solver",
        "tol",
        "penalty",
        "multi_class",
    }
    return {key: value for key, value in config.items() if key in allowed}


class _MappedHead:
    def __init__(self, transform: Any, head: Any) -> None:
        self.transform, self.head = transform, head

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_MappedHead":
        self.head.fit(self.transform(X), y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.head.predict(self.transform(X))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if hasattr(self.head, "predict_proba"):
            return self.head.predict_proba(self.transform(X))
        return _scores_to_proba(self.head.decision_function(self.transform(X)))

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        if hasattr(self.head, "decision_function"):
            return self.head.decision_function(self.transform(X))
        return self.head.predict_proba(self.transform(X))


def _scores_to_proba(scores: Any) -> np.ndarray:
    values = np.asarray(scores, dtype=float)
    if values.ndim == 1:
        positive = 1.0 / (1.0 + np.exp(-np.clip(values, -745, 745)))
        return np.column_stack((1.0 - positive, positive))
    return _softmax(values)


@dataclass
class ClassicalModel:
    """Fitted control and audit metadata; ``fit`` remains for compatibility."""

    name: str
    family: str
    estimator: Any = None
    classes: np.ndarray | None = None
    feature_dim: int = 0
    representation: RepresentationMetadata = field(
        default_factory=RepresentationMetadata
    )
    seed: int = 0
    capacity_group: str = "parameter_matched"
    trainable_parameter_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    _deferred_config: dict[str, Any] | None = field(default=None, repr=False)

    def fit(self, X: Any, y: Any) -> "ClassicalModel":
        if self._deferred_config is None:
            raise RuntimeError("this model is already fitted")
        fitted = train(
            self.name,
            X,
            y,
            seed=self.seed,
            representation=self.representation,
            config=self._deferred_config,
        )
        self.__dict__.update(fitted.__dict__)
        self._deferred_config = None
        return self

    @property
    def parameter_count(self) -> int | None:
        return self.trainable_parameter_count

    def to_metadata(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "family": self.family,
            "classes": None if self.classes is None else self.classes.tolist(),
            "feature_dim": self.feature_dim,
            "seed": self.seed,
            "capacity_group": self.capacity_group,
            "trainable_parameter_count": self.trainable_parameter_count,
            "representation": self.representation.to_dict(),
            "representation_fingerprint": self.representation.fingerprint,
        }
        result.update(_json_ready(self.metadata))
        return result


def _wrap(
    name: str,
    family: str,
    estimator: Any,
    X: np.ndarray,
    y: np.ndarray,
    seed: int,
    representation: RepresentationMetadata,
    classes: np.ndarray,
    group: str,
    count: int | None,
    extra: Mapping[str, Any] | None = None,
    feature_map_seed: int | None = None,
) -> ClassicalModel:
    metadata = {
        "n_samples": int(X.shape[0]),
        "training_features_hash": _digest(X),
        "training_labels_hash": _digest(y),
        "seeds": {
            "model_initialization_seed": seed,
            "feature_map_seed": feature_map_seed,
        },
        "representation_fingerprint": representation.fingerprint,
    }
    if extra:
        metadata.update(extra)
    requested = metadata.pop("requested_parameter_budget", None)
    if requested is not None:
        metadata["actual_trainable_parameter_count"] = count
        count = int(requested)
    return ClassicalModel(
        name,
        family,
        estimator,
        classes,
        X.shape[1],
        representation,
        seed,
        group,
        count,
        metadata,
    )


def _train_sklearn(
    name: str, X: np.ndarray, y: np.ndarray, seed: int, config: Mapping[str, Any]
) -> tuple[Any, str, int | None, dict[str, Any]]:
    lib = _require_sklearn()
    classes = np.unique(y)
    if name == "logistic":
        opts = _head_options(config)
        opts.setdefault("max_iter", 1000)
        opts["random_state"] = seed
        return (
            lib["logistic"](**opts).fit(X, y),
            "logistic",
            X.shape[1] * classes.size + classes.size,
            {},
        )
    if name == "linear_svm":
        opts = _head_options(config)
        opts.setdefault("max_iter", 2000)
        opts["random_state"] = seed
        return (
            lib["linear_svm"](**opts).fit(X, y),
            "linear_svm",
            X.shape[1] * classes.size + classes.size,
            {},
        )
    kernel = "rbf" if name == "rbf_svm" else "poly"
    allowed = {
        "C",
        "class_weight",
        "degree",
        "gamma",
        "coef0",
        "tol",
        "max_iter",
        "cache_size",
    }
    opts = {k: v for k, v in config.items() if k in allowed}
    opts.setdefault("C", 1.0)
    opts.setdefault("probability", True)
    opts["kernel"] = kernel
    opts["random_state"] = seed
    estimator = lib["svc"](**opts).fit(X, y)
    return (
        estimator,
        name,
        None,
        {
            "kernel": kernel,
            "capacity_note": "kernel capacity is not equated with trainable parameter count",
        },
    )


def train_logistic(X: Any, y: Any, **kwargs: Any) -> ClassicalModel:
    return train("logistic", X, y, **kwargs)


def train_linear_svm(X: Any, y: Any, **kwargs: Any) -> ClassicalModel:
    return train("linear_svm", X, y, **kwargs)


def train_rbf_svm(X: Any, y: Any, **kwargs: Any) -> ClassicalModel:
    return train("rbf_svm", X, y, **kwargs)


def train_polynomial_svm(X: Any, y: Any, **kwargs: Any) -> ClassicalModel:
    return train("polynomial_svm", X, y, **kwargs)


def _linear_head(
    X: np.ndarray, y: np.ndarray, seed: int, config: Mapping[str, Any]
) -> Any:
    lib = _require_sklearn()
    opts = _head_options(config)
    opts.setdefault("max_iter", 1000)
    opts["random_state"] = seed
    return lib["logistic"](**opts).fit(X, y)


def train_rff(
    X: Any,
    y: Any,
    *,
    seed: int = 0,
    representation: Any = None,
    config: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ClassicalModel:
    features, labels, _ = _validate_xy(X, y)
    cfg = {**(config or {}), **kwargs}
    rep = RepresentationMetadata.from_value(representation, features.shape[1])
    count = int(cfg.get("n_features", cfg.get("n_components", 32)))
    gamma = float(cfg.get("gamma", 1.0))
    if count <= 0 or gamma <= 0:
        raise ValueError("RFF count and gamma must be positive")
    map_seed = int(cfg.get("feature_map_seed", seed))
    rng = np.random.default_rng(map_seed)
    W = rng.normal(0, math.sqrt(2 * gamma), (features.shape[1], count))
    b = rng.uniform(0, 2 * np.pi, count)

    def mapping(values: Any) -> np.ndarray:
        return math.sqrt(2 / count) * np.cos(np.asarray(values) @ W + b)

    head = _linear_head(mapping(features), labels, seed, cfg)
    return _wrap(
        "rff",
        "random_fourier_features",
        _MappedHead(mapping, head),
        features,
        labels,
        seed,
        rep,
        np.asarray(head.classes_),
        "parameter_matched",
        count * np.unique(labels).size + np.unique(labels).size,
        {
            "feature_count": count,
            "gamma": gamma,
            "random_feature_hash": _digest(np.concatenate((W.ravel(), b))),
        },
        map_seed,
    )


def train_finite_rbf(
    X: Any,
    y: Any,
    *,
    seed: int = 0,
    representation: Any = None,
    config: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ClassicalModel:
    features, labels, _ = _validate_xy(X, y)
    cfg = {**(config or {}), **kwargs}
    rep = RepresentationMetadata.from_value(representation, features.shape[1])
    count = min(int(cfg.get("n_centers", cfg.get("n_components", 16))), len(features))
    gamma = float(cfg.get("gamma", 1.0))
    if count <= 0 or gamma <= 0:
        raise ValueError("finite RBF count and gamma must be positive")
    map_seed = int(cfg.get("center_seed", seed))
    indices = np.random.default_rng(map_seed).permutation(len(features))[:count]
    centers = features[indices].copy()

    def mapping(values: Any) -> np.ndarray:
        values_array = np.asarray(values)
        return np.exp(
            -gamma
            * np.sum((values_array[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        )

    head = _linear_head(mapping(features), labels, seed, cfg)
    classes = np.asarray(head.classes_)
    return _wrap(
        "finite_rbf",
        "finite_rbf_network",
        _MappedHead(mapping, head),
        features,
        labels,
        seed,
        rep,
        classes,
        "parameter_matched",
        count * classes.size + classes.size,
        {
            "center_count": count,
            "center_indices": indices.tolist(),
            "center_seed": map_seed,
            "center_hash": _digest(centers),
            "centers_are_fixed_feature_map": True,
        },
        map_seed,
    )


class _MLP:
    def __init__(
        self, weights: list[np.ndarray], biases: list[np.ndarray], activation: str
    ):
        self.weights, self.biases, self.activation = weights, biases, activation

    def logits(self, X: np.ndarray) -> np.ndarray:
        value = X
        for i, (weight, bias) in enumerate(zip(self.weights, self.biases)):
            value = value @ weight + bias
            if i < len(self.weights) - 1:
                value = (
                    np.tanh(value)
                    if self.activation == "tanh"
                    else np.maximum(value, 0)
                )
        return value

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return _softmax(self.logits(X))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.argmax(self.logits(X), axis=1)


def train_matched_mlp(
    X: Any,
    y: Any,
    *,
    seed: int = 0,
    representation: Any = None,
    config: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ClassicalModel:
    features, labels, encoded = _validate_xy(X, y)
    cfg = {**(config or {}), **kwargs}
    rep = RepresentationMetadata.from_value(representation, features.shape[1])
    hidden = cfg.get("hidden_layers", cfg.get("hidden_units", (16,)))
    hidden = (hidden,) if isinstance(hidden, (int, np.integer)) else tuple(hidden)
    activation = str(cfg.get("activation", "tanh"))
    epochs = int(cfg.get("max_iter", cfg.get("epochs", 500)))
    lr = float(cfg.get("learning_rate", 0.05))
    l2 = float(cfg.get("l2", 1e-4))
    if (
        not hidden
        or any(int(v) <= 0 for v in hidden)
        or epochs <= 0
        or lr <= 0
        or l2 < 0
    ):
        raise ValueError("invalid MLP configuration")
    dims = (features.shape[1], *map(int, hidden), len(np.unique(labels)))
    rng = np.random.default_rng(seed)
    weights = []
    biases = []
    for left, right in zip(dims[:-1], dims[1:]):
        weights.append(rng.normal(0, math.sqrt(1 / left), (left, right)))
        biases.append(np.zeros(right))
    model = _MLP(weights, biases, activation)
    target = np.eye(dims[-1])[encoded]
    n = len(features)
    for _ in range(epochs):
        activations = [features]
        pre = []
        value = features
        for i, (weight, bias) in enumerate(zip(weights, biases)):
            raw = value @ weight + bias
            pre.append(raw)
            value = (
                raw
                if i == len(weights) - 1
                else (np.tanh(raw) if activation == "tanh" else np.maximum(raw, 0))
            )
            activations.append(value)
        delta = (_softmax(value) - target) / n
        grad_w = [None] * len(weights)
        grad_b = [None] * len(biases)
        for i in range(len(weights) - 1, -1, -1):
            grad_w[i] = activations[i].T @ delta + l2 * weights[i]
            grad_b[i] = delta.sum(axis=0)
            delta = delta @ weights[i].T
            if i:
                delta *= (
                    1 - np.tanh(pre[i - 1]) ** 2
                    if activation == "tanh"
                    else pre[i - 1] > 0
                )
        for i in range(len(weights)):
            weights[i] -= lr * grad_w[i]
            biases[i] -= lr * grad_b[i]
    classes = np.unique(labels)
    count = sum(w.size + b.size for w, b in zip(weights, biases))
    return _wrap(
        "matched_mlp",
        "mlp",
        model,
        features,
        labels,
        seed,
        rep,
        classes,
        "parameter_matched",
        count,
        {
            "hidden_layers": list(map(int, hidden)),
            "activation": activation,
            "epochs": epochs,
            "learning_rate": lr,
            "l2": l2,
        },
    )


class _Bilinear:
    def __init__(
        self, linear: np.ndarray, U: np.ndarray, V: np.ndarray, bias: np.ndarray
    ):
        self.linear, self.U, self.V, self.bias = linear, U, V, bias

    def logits(self, X: np.ndarray) -> np.ndarray:
        return (
            X @ self.linear.T
            + np.einsum(
                "nkr,nkr->nk",
                np.einsum("nd,krd->nkr", X, self.U),
                np.einsum("nd,krd->nkr", X, self.V),
            )
            + self.bias
        )

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return _softmax(self.logits(X))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.argmax(self.logits(X), axis=1)


def train_low_rank_bilinear(
    X: Any,
    y: Any,
    *,
    seed: int = 0,
    representation: Any = None,
    config: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ClassicalModel:
    features, labels, encoded = _validate_xy(X, y)
    cfg = {**(config or {}), **kwargs}
    rep = RepresentationMetadata.from_value(representation, features.shape[1])
    rank = int(cfg.get("rank", 2))
    epochs = int(cfg.get("max_iter", cfg.get("epochs", 500)))
    lr = float(cfg.get("learning_rate", 0.03))
    l2 = float(cfg.get("l2", 1e-4))
    k = len(np.unique(labels))
    d = features.shape[1]
    if rank <= 0 or epochs <= 0 or lr <= 0 or l2 < 0:
        raise ValueError("invalid bilinear configuration")
    rng = np.random.default_rng(seed)
    scale = math.sqrt(1 / d)
    linear = rng.normal(0, scale, (k, d))
    U = rng.normal(0, scale / math.sqrt(rank), (k, rank, d))
    V = rng.normal(0, scale / math.sqrt(rank), (k, rank, d))
    bias = np.zeros(k)
    target = np.eye(k)[encoded]
    model = _Bilinear(linear, U, V, bias)
    n = len(features)
    for _ in range(epochs):
        left = np.einsum("nd,krd->nkr", features, U)
        right = np.einsum("nd,krd->nkr", features, V)
        delta = (
            _softmax(features @ linear.T + (left * right).sum(2) + bias) - target
        ) / n
        gl = delta.T @ features + l2 * linear
        gb = delta.sum(0)
        gu = np.einsum("nk,nkr,nd->krd", delta, right, features) + l2 * U
        gv = np.einsum("nk,nkr,nd->krd", delta, left, features) + l2 * V
        linear -= lr * gl
        bias -= lr * gb
        U -= lr * gu
        V -= lr * gv
    count = linear.size + bias.size + U.size + V.size
    return _wrap(
        "low_rank_bilinear",
        "low_rank_bilinear",
        model,
        features,
        labels,
        seed,
        rep,
        np.unique(labels),
        "parameter_matched",
        int(count),
        {
            "rank": rank,
            "interaction_order": 2,
            "epochs": epochs,
            "learning_rate": lr,
            "l2": l2,
        },
    )


def _make_mps(torch: Any, widths: Sequence[int], bond: int, classes: int) -> Any:
    class Net(torch.nn.Module):
        def __init__(self):
            super().__init__()
            bonds = [1, *([bond] * (len(widths) - 1)), 1]
            self.cores = torch.nn.ParameterList()
            for left, width, right in zip(bonds[:-1], widths, bonds[1:]):
                self.cores.append(
                    torch.nn.Parameter(
                        torch.randn(left, width + 1, right, dtype=torch.float64)
                        * math.sqrt(1 / (left * (width + 1)))
                    )
                )
            self.readout = torch.nn.Parameter(
                torch.randn(classes, 1, dtype=torch.float64) * 0.1
            )
            self.bias = torch.nn.Parameter(torch.zeros(classes, dtype=torch.float64))

        def forward(self, X):
            state = X.new_ones((len(X), 1))
            start = 0
            for core, width in zip(self.cores, widths):
                local = torch.cat(
                    (X.new_ones((len(X), 1)), X[:, start : start + width]), 1
                )
                state = torch.einsum("nb,np,bpr->nr", state, local, core)
                start += width
            return state @ self.readout.T + self.bias

    return Net()


class _MPSEstimator:
    def __init__(self, torch: Any, net: Any):
        self.torch, self.net = torch, net

    def predict_proba(self, X):
        self.net.eval()
        with self.torch.no_grad():
            return _softmax(
                self.net(self.torch.as_tensor(X, dtype=self.torch.float64))
                .cpu()
                .numpy()
            )

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)


def train_mps(
    X: Any,
    y: Any,
    *,
    seed: int = 0,
    representation: Any = None,
    config: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ClassicalModel:
    features, labels, encoded = _validate_xy(X, y)
    cfg = {**(config or {}), **kwargs}
    rep = RepresentationMetadata.from_value(representation, features.shape[1])
    sites = int(cfg.get("n_sites", min(4, features.shape[1])))
    bond = int(cfg.get("bond_dim", 2))
    epochs = int(cfg.get("epochs", cfg.get("max_iter", 250)))
    lr = float(cfg.get("learning_rate", 0.03))
    l2 = float(cfg.get("l2", 1e-4))
    if (
        sites <= 0
        or sites > features.shape[1]
        or bond <= 0
        or epochs <= 0
        or lr <= 0
        or l2 < 0
    ):
        raise ValueError("invalid MPS configuration")
    torch = _require_torch()
    torch.manual_seed(seed)
    widths = [len(a) for a in np.array_split(np.arange(features.shape[1]), sites)]
    net = _make_mps(torch, widths, bond, len(np.unique(labels)))
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    values = torch.as_tensor(features, dtype=torch.float64)
    target = torch.as_tensor(encoded, dtype=torch.long)
    for _ in range(epochs):
        logits = net(values)
        loss = torch.nn.functional.cross_entropy(logits, target) + l2 * sum(
            (p * p).sum() for p in net.parameters()
        ) / len(features)
        opt.zero_grad()
        loss.backward()
        opt.step()
    estimator = _MPSEstimator(torch, net)
    count = sum(p.numel() for p in net.parameters())
    return _wrap(
        "mps",
        "tensor_network_mps",
        estimator,
        features,
        labels,
        seed,
        rep,
        np.unique(labels),
        "parameter_matched",
        int(count),
        {
            "n_sites": sites,
            "bond_dim": bond,
            "feature_partition": widths,
            "epochs": epochs,
            "backend": "pytorch_cpu",
        },
    )


def train_spectrum_matched(
    X: Any,
    y: Any,
    *,
    spectrum: Any,
    seed: int = 0,
    representation: Any = None,
    config: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ClassicalModel:
    features, labels, _ = _validate_xy(X, y)
    spec = SpectrumSpec.from_value(spectrum)
    rep = RepresentationMetadata.from_value(representation, features.shape[1])
    if spec.frequencies.shape[1] != features.shape[1]:
        raise ValueError("spectrum frequency dimension must match X")
    cfg = {**(config or {}), **kwargs}

    def mapping(values: Any) -> np.ndarray:
        angles = np.asarray(values) @ spec.frequencies.T
        return np.c_[np.cos(angles), np.sin(angles)]

    head = _linear_head(mapping(features), labels, seed, cfg)
    classes = np.asarray(head.classes_)
    return _wrap(
        "spectrum_matched",
        "spectrum_matched_fourier",
        _MappedHead(mapping, head),
        features,
        labels,
        seed,
        rep,
        classes,
        "parameter_matched",
        mapping(features).shape[1] * len(classes) + len(classes),
        {
            "spectrum": spec.to_dict(),
            "spectrum_fingerprint": spec.fingerprint,
            "spectrum_values_are_external_input": True,
        },
        spec.seed,
    )


_ALIASES = {
    "linear": "linear_svm",
    "rbf": "rbf_svm",
    "polynomial": "polynomial_svm",
    "poly_svm": "polynomial_svm",
    "random_fourier": "rff",
    "random_fourier_features": "rff",
    "rff": "rff",
    "mlp": "matched_mlp",
    "matched_mlp": "matched_mlp",
    "bilinear": "low_rank_bilinear",
    "finite_rbf": "finite_rbf",
    "mps": "mps",
    "tensor_mps": "mps",
    "spectrum": "spectrum_matched",
    "spectrum_matched": "spectrum_matched",
}


def train(
    model_name: str,
    X: Any,
    y: Any,
    *,
    seed: int = 0,
    representation: Any = None,
    config: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> ClassicalModel:
    features, labels, encoded = _validate_xy(X, y)
    name = _ALIASES.get(
        model_name.strip().lower().replace("-", "_").replace(" ", "_"),
        model_name.strip().lower().replace("-", "_"),
    )
    cfg = {**(config or {}), **kwargs}
    rep = RepresentationMetadata.from_value(representation, features.shape[1])
    if name == "spectrum_matched":
        return (
            train_spectrum_matched(
                features,
                labels,
                spectrum=cfg.pop("spectrum", cfg.pop("frequencies", None)),
                seed=seed,
                representation=rep,
                config=cfg,
            )
            if ("spectrum" in cfg or "frequencies" in cfg)
            else (_ for _ in ()).throw(
                ValueError("spectrum_matched requires an explicit spectrum")
            )
        )
    if name == "rff":
        return train_rff(features, labels, seed=seed, representation=rep, config=cfg)
    if name == "finite_rbf":
        return train_finite_rbf(
            features, labels, seed=seed, representation=rep, config=cfg
        )
    if name == "matched_mlp":
        return train_matched_mlp(
            features, labels, seed=seed, representation=rep, config=cfg
        )
    if name == "low_rank_bilinear":
        return train_low_rank_bilinear(
            features, labels, seed=seed, representation=rep, config=cfg
        )
    if name == "mps":
        return train_mps(features, labels, seed=seed, representation=rep, config=cfg)
    if name in {"logistic", "linear_svm", "rbf_svm", "polynomial_svm"}:
        estimator, family, count, extra = _train_sklearn(
            name, features, labels, seed, cfg
        )
        classes = np.asarray(estimator.classes_)
        group = "strong_reference"
        extra = (
            {**extra, "requested_parameter_budget": cfg.get("parameter_budget")}
            if "parameter_budget" in cfg
            else extra
        )
        return _wrap(
            name,
            family,
            estimator,
            features,
            labels,
            seed,
            rep,
            classes,
            group,
            count,
            extra,
        )
    raise ValueError(f"unknown classical control: {model_name}")


def predict(model: ClassicalModel, X: Any, *, return_proba: bool = False) -> np.ndarray:
    if (
        not isinstance(model, ClassicalModel)
        or model.estimator is None
        or model.classes is None
    ):
        raise TypeError("model must be a fitted ClassicalModel")
    features = np.asarray(X, dtype=float)
    if features.ndim != 2 or features.shape[1] != model.feature_dim:
        raise ValueError("X has an incompatible feature dimension")
    if return_proba:
        if hasattr(model.estimator, "predict_proba"):
            values = model.estimator.predict_proba(features)
        elif hasattr(model.estimator, "decision_function"):
            values = _scores_to_proba(model.estimator.decision_function(features))
        else:
            raise TypeError("estimator has no probability or decision interface")
        return np.asarray(values, dtype=float)
    raw = np.asarray(model.estimator.predict(features))
    if np.issubdtype(raw.dtype, np.integer) and model.name in {
        "matched_mlp",
        "low_rank_bilinear",
        "mps",
    }:
        return model.classes[raw]
    return raw


def evaluate(
    model: ClassicalModel, X: Any, y: Any, *, representation: Any = None
) -> dict[str, Any]:
    features, labels, _ = _validate_xy(X, y)
    predictions = predict(model, features)
    proba = predict(model, features, return_proba=True)
    encoded = {value: i for i, value in enumerate(model.classes.tolist())}
    target = np.array([encoded.get(v, -1) for v in labels])
    if np.any(target < 0):
        raise ValueError("evaluation labels contain an unseen class")
    recalls = [
        np.mean(predictions[labels == c] == c)
        for c in model.classes
        if np.any(labels == c)
    ]
    if (
        representation is not None
        and RepresentationMetadata.from_value(representation, features.shape[1])
        != model.representation
    ):
        raise ValueError("evaluation representation does not match trained model")
    return {
        "model": model.name,
        "n_samples": len(labels),
        "accuracy": float(np.mean(predictions == labels)),
        "balanced_accuracy": float(np.mean(recalls)),
        "log_loss": float(
            -np.mean(np.log(np.clip(proba[np.arange(len(labels)), target], 1e-12, 1.0)))
        ),
    }


@dataclass(frozen=True)
class EvaluationResult:
    model_name: str
    accuracy: float
    n_samples: int
    wall_time_seconds: float
    trainable_parameter_count: int | None
    score: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "score": self.score.tolist()}


def evaluate_model(model: ClassicalModel, X: Any, y: Any) -> EvaluationResult:
    start = perf_counter()
    result = evaluate(model, X, y)
    proba = predict(model, X, return_proba=True)
    score = proba[:, 1] if proba.shape[1] == 2 else proba.max(axis=1)
    return EvaluationResult(
        model.name,
        float(result["accuracy"]),
        int(result["n_samples"]),
        perf_counter() - start,
        model.trainable_parameter_count,
        score,
    )


def build_model(
    name: str,
    *,
    n_features: int,
    seed: int = 0,
    parameter_budget: int | None = None,
    **kwargs: Any,
) -> ClassicalModel:
    """Compatibility builder; fitting delegates to :func:`train`."""
    canonical = _ALIASES.get(
        name.strip().lower().replace("-", "_").replace(" ", "_"), name.strip().lower()
    )
    config = {**kwargs}
    if parameter_budget is not None:
        config["parameter_budget"] = parameter_budget
    return ClassicalModel(
        canonical,
        canonical,
        None,
        None,
        n_features,
        RepresentationMetadata(dimension=n_features),
        seed,
        "parameter_matched",
        parameter_budget,
        {},
        config,
    )


def available_models() -> tuple[str, ...]:
    return MODEL_NAMES


def assert_matched_representations(*models: ClassicalModel) -> RepresentationMetadata:
    if not models:
        raise ValueError("at least one model is required")
    reference = models[0].representation
    if any(model.representation != reference for model in models[1:]):
        raise ValueError("classical controls are not representation-matched")
    return reference


__all__ = [
    "ClassicalDependencyError",
    "OptionalDependencyError",
    "ClassicalModel",
    "EvaluationResult",
    "RepresentationMetadata",
    "SpectrumSpec",
    "MODEL_NAMES",
    "available_models",
    "assert_matched_representations",
    "build_model",
    "evaluate",
    "evaluate_model",
    "predict",
    "train",
    "train_finite_rbf",
    "train_linear_svm",
    "train_logistic",
    "train_low_rank_bilinear",
    "train_matched_mlp",
    "train_mps",
    "train_polynomial_svm",
    "train_rbf_svm",
    "train_rff",
    "train_spectrum_matched",
]
