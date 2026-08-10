from __future__ import annotations

import numpy as np
import pytest

from research.qatelier.data.representations import CompressorArtifact, FrozenRepresentationManifest, make_pair_representation


def test_compressor_fits_train_only_and_reuses_the_same_transform(tmp_path):
    rng = np.random.default_rng(12)
    train = rng.normal(size=(12, 5))
    validation = rng.normal(loc=10, size=(4, 5))
    artifact = CompressorArtifact.fit(train, train_sample_ids=[f"train-{i}" for i in range(12)], output_dim=3, whiten=True)
    transformed = artifact.transform(validation)
    assert transformed.shape == (4, 3)
    assert artifact.fit_split == "train"
    assert artifact.to_metadata()["fit_features_hash"]
    with pytest.raises(ValueError, match="train"):
        CompressorArtifact.fit(train, train_sample_ids=[f"train-{i}" for i in range(12)], output_dim=3, fit_split="validation")
    with pytest.raises(FileExistsError):
        path = artifact.save(tmp_path / "compressor.npz")
        artifact.save(path)


def test_pair_representation_has_declared_layout():
    query = np.array([[1.0, 2.0]])
    document = np.array([[3.0, 5.0]])
    np.testing.assert_array_equal(make_pair_representation(query, document), [[1, 2, 3, 5, 2, 3, 3, 10]])


def test_frozen_manifest_requires_exact_encoder_identity():
    manifest = FrozenRepresentationManifest("sentence-transformers/test", "rev-1", "sha256:test", 4, {"max_length": 128}, "mean", "l2", "ids", "embeddings")
    assert len(manifest.manifest_hash) == 64
    with pytest.raises(ValueError):
        FrozenRepresentationManifest("model", "", "digest", 4, {}, "mean", "none", "ids", "embeddings")
