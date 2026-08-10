from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from research.qatelier.classical import (
    RepresentationMetadata,
    SpectrumSpec,
    assert_matched_representations,
    build_model,
    evaluate,
    evaluate_model,
    predict,
    train,
    train_logistic,
    train_mps,
    train_rff,
    train_spectrum_matched,
)


def _data():
    rng = np.random.default_rng(17)
    X = rng.normal(size=(48, 4))
    y = ((X[:, 0] * X[:, 1] + 0.25 * X[:, 2]) > 0).astype(int)
    return X, y


def _rep():
    return RepresentationMetadata(
        "frozen-toy", 4, "pca", "digest", "split-0", source="test"
    )


def test_optional_backends_are_lazy():
    code = "import sys; import research.qatelier.classical.models; print(int('sklearn' in sys.modules), int('torch' in sys.modules))"
    result = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )
    assert result.stdout.strip() == "0 0"


def test_train_predict_evaluate_and_metadata_are_deterministic():
    X, y = _data()
    first = train_rff(X, y, seed=9, representation=_rep(), n_features=8)
    second = train_rff(X, y, seed=9, representation=_rep(), n_features=8)
    assert first.to_metadata() == second.to_metadata()
    np.testing.assert_array_equal(predict(first, X), predict(second, X))
    assert evaluate(first, X, y, representation=_rep())["n_samples"] == len(y)
    assert_matched_representations(first, second)
    with pytest.raises(ValueError, match="representation-matched"):
        assert_matched_representations(
            first,
            train_logistic(
                X, y, representation={**_rep().to_dict(), "split_id": "other"}
            ),
        )


@pytest.mark.parametrize(
    "name, config",
    [
        ("logistic", {}),
        ("linear_svm", {}),
        ("rbf_svm", {"probability": True}),
        ("polynomial_svm", {"degree": 2, "probability": True}),
        ("rff", {"n_features": 8}),
        ("matched_mlp", {"hidden_layers": (5,), "max_iter": 30}),
        ("low_rank_bilinear", {"rank": 1, "max_iter": 30}),
        ("finite_rbf", {"n_centers": 6}),
    ],
)
def test_all_declared_non_mps_controls_work(name, config):
    X, y = _data()
    model = train(name, X, y, seed=3, representation=_rep(), **config)
    metrics = evaluate(model, X, y)
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert predict(model, X).shape == y.shape
    assert predict(model, X, return_proba=True).shape == (len(y), 2)


def test_kernel_controls_are_strong_references_not_parameter_matches():
    X, y = _data()
    model = train("rbf_svm", X, y, representation=_rep(), probability=True)
    assert model.capacity_group == "strong_reference"
    assert model.trainable_parameter_count is None
    assert "not equated" in model.metadata["capacity_note"]


def test_spectrum_interface_requires_external_support_and_records_it():
    X, y = _data()
    spec = SpectrumSpec(np.eye(4)[:2], "diagnostic", "toy", 12)
    model = train_spectrum_matched(X, y, spectrum=spec, representation=_rep())
    assert model.metadata["spectrum_fingerprint"] == spec.fingerprint
    assert model.metadata["spectrum_values_are_external_input"] is True
    with pytest.raises(ValueError, match="frequency dimension"):
        train_spectrum_matched(X, y, spectrum=np.ones((2, 3)))


def test_legacy_build_and_evaluate_api_remains_usable():
    X, y = _data()
    model = build_model("logistic", n_features=4, seed=4, parameter_budget=12)
    result = evaluate_model(model.fit(X, y), X, y)
    assert result.trainable_parameter_count == 12
    assert result.score.shape == (len(y),)


def test_mps_is_a_real_optional_control_when_torch_is_available():
    pytest.importorskip("torch")
    X, y = _data()
    model = train_mps(X, y, seed=2, representation=_rep(), n_sites=2, epochs=8)
    assert model.family == "tensor_network_mps"
    assert model.trainable_parameter_count > 0
    assert np.isfinite(evaluate(model, X, y)["log_loss"])
