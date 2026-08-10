"""Auditable frozen representations and train-only PCA compression."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


def stable_array_hash(array: np.ndarray) -> str:
    """Hash dtype, shape, and bytes in a platform-stable representation."""

    value = np.ascontiguousarray(np.asarray(array))
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(repr(value.shape).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


@dataclass(frozen=True)
class FrozenRepresentationManifest:
    """Identity and extraction settings for a frozen embedding artifact."""

    encoder_model_id: str
    encoder_revision: str
    weights_digest: str
    embedding_dim: int
    tokenizer_settings: Mapping[str, Any]
    pooling: str
    normalization: str
    sample_ids_hash: str
    embeddings_hash: str

    def __post_init__(self) -> None:
        if not self.encoder_model_id or not self.encoder_revision or not self.weights_digest:
            raise ValueError("encoder model id, exact revision, and weights digest are required")
        if self.embedding_dim < 1:
            raise ValueError("embedding_dim must be positive")
        if not self.pooling or not self.normalization:
            raise ValueError("pooling and normalization settings are required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def manifest_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class CompressorArtifact:
    """Immutable PCA/whitening transform fit exclusively on training rows."""

    method: str
    input_dim: int
    output_dim: int
    fit_split: str
    fit_sample_ids_hash: str
    fit_features_hash: str
    mean: np.ndarray
    components: np.ndarray
    scale: np.ndarray
    whiten: bool
    artifact_hash: str

    def __post_init__(self) -> None:
        if self.method != "pca":
            raise ValueError("only the deterministic PCA compressor is implemented")
        if self.fit_split != "train":
            raise ValueError("compressor fitting is restricted to the train split")
        if self.input_dim < 1 or self.output_dim < 1 or self.output_dim > self.input_dim:
            raise ValueError("invalid compressor dimensions")
        if self.mean.shape != (self.input_dim,):
            raise ValueError("mean has the wrong shape")
        if self.components.shape != (self.output_dim, self.input_dim):
            raise ValueError("components have the wrong shape")
        if self.scale.shape != (self.output_dim,) or np.any(self.scale <= 0):
            raise ValueError("scale must contain positive values")

    @classmethod
    def fit(
        cls,
        train_features: np.ndarray,
        *,
        train_sample_ids: Sequence[str],
        output_dim: int,
        whiten: bool = False,
        fit_split: str = "train",
    ) -> "CompressorArtifact":
        if fit_split != "train":
            raise ValueError("fit_split must be exactly 'train'")
        features = np.asarray(train_features, dtype=np.float64)
        if features.ndim != 2 or features.shape[0] < 2 or not np.all(np.isfinite(features)):
            raise ValueError("train_features must be finite, two-dimensional, and contain at least two rows")
        ids = tuple(str(item) for item in train_sample_ids)
        if len(ids) != features.shape[0] or len(set(ids)) != len(ids):
            raise ValueError("train_sample_ids must be unique and aligned to training rows")
        if not isinstance(output_dim, int) or isinstance(output_dim, bool) or not 1 <= output_dim <= min(features.shape):
            raise ValueError("output_dim must not exceed the training matrix rank bounds")
        mean = features.mean(axis=0)
        centered = features - mean
        _, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
        components = vh[:output_dim].copy()
        scale = singular_values[:output_dim] / np.sqrt(max(features.shape[0] - 1, 1))
        scale = np.where(scale > np.finfo(float).eps, scale, 1.0)
        ids_hash = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
        payload = {
            "method": "pca",
            "input_dim": features.shape[1],
            "output_dim": output_dim,
            "fit_split": "train",
            "fit_sample_ids_hash": ids_hash,
            "fit_features_hash": stable_array_hash(features),
            "whiten": bool(whiten),
            "mean": stable_array_hash(mean),
            "components": stable_array_hash(components),
            "scale": stable_array_hash(scale),
        }
        artifact_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls("pca", features.shape[1], output_dim, "train", ids_hash, stable_array_hash(features), mean, components, scale, bool(whiten), artifact_hash)

    def transform(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != self.input_dim:
            raise ValueError(f"features must have shape (n, {self.input_dim})")
        projected = (values - self.mean) @ self.components.T
        return projected / self.scale if self.whiten else projected

    def to_metadata(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "input_dim": self.input_dim,
            "output_dim": self.output_dim,
            "fit_split": self.fit_split,
            "fit_sample_ids_hash": self.fit_sample_ids_hash,
            "fit_features_hash": self.fit_features_hash,
            "whiten": self.whiten,
            "artifact_hash": self.artifact_hash,
        }

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"compressor artifact is immutable: {destination}")
        np.savez_compressed(
            destination,
            metadata=json.dumps(self.to_metadata(), sort_keys=True),
            mean=self.mean,
            components=self.components,
            scale=self.scale,
        )
        return destination

    @classmethod
    def load(cls, path: str | Path) -> "CompressorArtifact":
        """Load and validate an immutable compressor artifact."""

        source = Path(path)
        with np.load(source, allow_pickle=False) as payload:
            metadata = json.loads(str(payload["metadata"].item()))
            artifact = cls(
                method=str(metadata["method"]),
                input_dim=int(metadata["input_dim"]),
                output_dim=int(metadata["output_dim"]),
                fit_split=str(metadata["fit_split"]),
                fit_sample_ids_hash=str(metadata["fit_sample_ids_hash"]),
                fit_features_hash=str(metadata["fit_features_hash"]),
                mean=np.asarray(payload["mean"], dtype=float),
                components=np.asarray(payload["components"], dtype=float),
                scale=np.asarray(payload["scale"], dtype=float),
                whiten=bool(metadata["whiten"]),
                artifact_hash=str(metadata["artifact_hash"]),
            )
        if artifact.to_metadata() != metadata:
            raise ValueError(f"compressor metadata mismatch: {source}")
        return artifact


def make_pair_representation(query_embeddings: np.ndarray, document_embeddings: np.ndarray) -> np.ndarray:
    """Build the shared query/document interaction representation."""

    query = np.asarray(query_embeddings, dtype=np.float64)
    document = np.asarray(document_embeddings, dtype=np.float64)
    if query.ndim != 2 or document.shape != query.shape:
        raise ValueError("query and document embeddings must have identical 2-D shapes")
    return np.concatenate((query, document, np.abs(query - document), query * document), axis=1)


__all__ = ["CompressorArtifact", "FrozenRepresentationManifest", "make_pair_representation", "stable_array_hash"]
