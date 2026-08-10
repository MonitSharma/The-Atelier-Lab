import json

from research.qatelier.baselines import (
    BASELINE_REGISTRY,
    build_default_registry,
    get_baseline,
    list_baselines,
)


EXPECTED_BASELINES = {
    "linear",
    "rbf",
    "polynomial",
    "random_fourier",
    "mlp",
    "bilinear",
    "spectrum_matched",
}
EXPECTED_ORDER = (
    "linear",
    "rbf",
    "polynomial",
    "random_fourier",
    "mlp",
    "bilinear",
    "spectrum_matched",
)


def test_registry_is_complete_and_names_are_unique():
    specs = list_baselines()

    assert {spec.name for spec in specs} == EXPECTED_BASELINES
    assert len(specs) == len(EXPECTED_BASELINES)
    assert set(BASELINE_REGISTRY.names) == EXPECTED_BASELINES
    assert all(spec.family and spec.description for spec in specs)


def test_matching_metadata_is_explicit_for_every_control():
    for spec in list_baselines():
        parameter_budget = spec.parameter_budget
        search_budget = spec.search_budget

        assert parameter_budget.mode == "exact"
        assert parameter_budget.reference == "selected_quantum_adapter"
        assert parameter_budget.count_formula == "resolved_to_equal_trainable_parameter_count"
        assert search_budget.mode == "matched"
        assert search_budget.reference == "selected_quantum_adapter"
        assert search_budget.selection_split == "validation"
        assert search_budget.selection_metric == "pre_registered_primary_metric"


def test_registry_serialization_is_stable_and_json_safe():
    first = build_default_registry().to_json()
    second = build_default_registry().serialize()

    assert first == second
    payload = json.loads(first)
    assert payload["schema_version"] == 1
    assert [item["name"] for item in payload["baselines"]] == list(EXPECTED_ORDER)
    assert all(isinstance(item["aliases"], list) for item in payload["baselines"])
    random_fourier = payload["baselines"][3]
    assert "random_fourier_features" in random_fourier["aliases"]
    assert get_baseline("random-fourier").name == "random_fourier"
