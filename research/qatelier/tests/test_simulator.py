import numpy as np
import pytest

from research.qatelier.quantum_adapter import (
    EncodingSpec,
    QuantumAdapterConfig,
    ReadoutSpec,
)
from research.qatelier.simulation import (
    CircuitSchedule,
    PQCStatevectorSimulator,
    aer_available,
    cross_validate_aer,
    initialize_parameters,
    simulate,
)


def test_parameter_layout_is_exact_and_matches_existing_resource_count():
    config = QuantumAdapterConfig(
        q=2,
        R=2,
        L=2,
        encoding=EncodingSpec(trainable_scale=True),
        readout=ReadoutSpec(("Z0", "X[1]"), trainable_weights=True, trainable_bias=True),
        family="QIA-L",
    )
    schedule = CircuitSchedule.from_config(config)

    assert schedule.parameter_layout.names == (
        "encoding.scale[0]",
        "encoding.scale[1]",
        "layer[0].qubit[0].RX",
        "layer[0].qubit[0].RY",
        "layer[0].qubit[0].RZ",
        "layer[0].qubit[1].RX",
        "layer[0].qubit[1].RY",
        "layer[0].qubit[1].RZ",
        "layer[1].qubit[0].RX",
        "layer[1].qubit[0].RY",
        "layer[1].qubit[0].RZ",
        "layer[1].qubit[1].RX",
        "layer[1].qubit[1].RY",
        "layer[1].qubit[1].RZ",
        "readout.weight[0]",
        "readout.weight[1]",
        "readout.bias",
    )
    assert schedule.parameter_layout.size == config.resources().trainable_parameters


def test_qia_schedules_count_disjoint_rounds_and_scheduled_depth():
    expected = {
        "QIA-P": (0, 0),
        "QIA-L": (3, 2),
        "QIA-X": (3, 2),
        "QIA-A": (6, 3),
    }
    for family, (gate_count, round_count) in expected.items():
        config = QuantumAdapterConfig(q=4, R=1, L=1, family=family)
        resources = CircuitSchedule.from_config(config).resources
        assert resources.two_qubit_gates == gate_count
        assert resources.two_qubit_rounds_per_block == round_count
        assert resources.two_qubit_depth == round_count
        assert resources.logical_depth == 2 + 3 + round_count
        assert resources.adapter_declared_depth == 2 + 3 + int(gate_count > 0)


def test_exact_expectation_and_observable_order_are_deterministic():
    config = QuantumAdapterConfig(q=2, R=1, L=1, family="QIA-P", readout=ReadoutSpec(("Z0", "X1", "Y0")))
    theta = np.zeros(config.resources().trainable_parameters)
    result = simulate(config, [0.0, 0.0], theta, return_statevector=True)

    assert result.observable_order == ("Z0", "X1", "Y0")
    np.testing.assert_allclose(result.raw_expectations, [1.0, 0.0, 0.0], atol=1e-12)
    assert result.shots is None
    assert result.counts is None
    np.testing.assert_allclose(result.statevector, [1.0, 0.0, 0.0, 0.0], atol=1e-12)


def test_trainable_encoding_and_readout_parameters_are_used_in_documented_order():
    config = QuantumAdapterConfig(
        q=1,
        R=1,
        L=1,
        encoding=EncodingSpec(trainable_scale=True),
        readout=ReadoutSpec(("Z0",), trainable_weights=True, trainable_bias=True),
    )
    simulator = PQCStatevectorSimulator(config)
    theta = np.array([2.0, 0.0, 0.0, 0.0, 3.0, 0.5])
    result = simulator.run([0.4], theta)
    # RY(2 * 0.4) followed by zero trainable rotations gives cos(0.8).
    expected_raw = np.cos(0.8)
    np.testing.assert_allclose(result.raw_expectations, [expected_raw], atol=1e-12)
    np.testing.assert_allclose(result.expectations, [3.0 * expected_raw + 0.5], atol=1e-12)


def test_finite_shots_return_counts_and_converge_to_exact_expectations():
    config = QuantumAdapterConfig(q=2, R=1, L=1, family="QIA-L", readout=ReadoutSpec(("Z0", "X1", "Y0")))
    theta = np.linspace(-0.3, 0.4, config.resources().trainable_parameters)
    exact = simulate(config, [0.31, -0.22], theta)
    finite = simulate(config, [0.31, -0.22], theta, shots=50000, seed=23)

    assert finite.shots == 50000
    assert finite.seed == 23
    assert finite.counts is not None
    assert len(finite.counts) == 3
    assert all(sum(counts.values()) == 50000 for counts in finite.counts)
    np.testing.assert_allclose(finite.raw_expectations, exact.raw_expectations, atol=0.03)


def test_batch_execution_uses_independent_deterministic_shot_seeds():
    config = QuantumAdapterConfig(q=2, R=1, L=1)
    theta = initialize_parameters(config, seed=4)
    simulator = PQCStatevectorSimulator(config)
    first = np.vstack(
        [simulator.run(row, theta, shots=100, seed=10 + i).expectations for i, row in enumerate([[0.1, 0.2], [0.3, 0.4]])]
    )
    from research.qatelier.simulation import simulate_batch

    second = simulate_batch(config, [[0.1, 0.2], [0.3, 0.4]], theta, shots=100, seed=10)
    np.testing.assert_array_equal(first, second)


def test_schedule_and_result_json_roundtrip_without_framework_imports():
    config = QuantumAdapterConfig(q=2, R=1, L=1, family="QIA-A")
    schedule = CircuitSchedule.from_config(config)
    restored_schedule = CircuitSchedule.from_json(schedule.to_json())
    assert restored_schedule.to_json() == schedule.to_json()

    result = simulate(config, [0.2, -0.1], np.zeros(config.resources().trainable_parameters), return_statevector=True)
    restored_result = type(result).from_json(result.to_json())
    np.testing.assert_allclose(restored_result.expectations, result.expectations)
    np.testing.assert_allclose(restored_result.statevector, result.statevector)
    assert restored_result.resources.to_dict() == result.resources.to_dict()


@pytest.mark.skipif(not aer_available(), reason="optional qiskit-aer dependency is unavailable")
def test_exact_numpy_path_agrees_with_qiskit_aer():
    config = QuantumAdapterConfig(q=3, R=2, L=1, family="QIA-A", readout=ReadoutSpec(("Z0", "X[1]", "Y2")))
    theta = initialize_parameters(config, seed=8)
    report = cross_validate_aer(config, [0.17, -0.29, 0.41], theta, atol=1e-8)
    assert report["passed"], report
    assert report["max_abs_error"] < 1e-8
