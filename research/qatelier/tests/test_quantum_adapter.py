import dataclasses

import numpy as np
import pytest

from research.qatelier.quantum_adapter import (
    BackendNeutralAdapter,
    EncodingSpec,
    EntanglementFamily,
    QuantumAdapterConfig,
    ReadoutSpec,
    entangling_pairs,
)


def test_configuration_is_immutable_and_normalizes_contract_values():
    config = QuantumAdapterConfig(q=4, R=2, L=3, family="qia-l")

    assert dataclasses.is_dataclass(config)
    assert config.family is EntanglementFamily.QIA_L
    assert config.reupload_count == 2
    assert config.trainable_block_count == 3
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.q = 5


def test_family_schedules_and_resource_counts_are_distinct():
    counts = {}
    for family in EntanglementFamily:
        config = QuantumAdapterConfig(q=4, R=2, L=3, family=family)
        counts[family] = config.resources().two_qubit_gates

    assert counts == {
        EntanglementFamily.QIA_P: 0,
        EntanglementFamily.QIA_L: 9,
        EntanglementFamily.QIA_X: 9,
        EntanglementFamily.QIA_A: 18,
    }
    assert entangling_pairs(4, "QIA-X") == ((0, 2), (0, 3), (1, 3))
    assert counts[EntanglementFamily.QIA_X] > counts[EntanglementFamily.QIA_P]
    assert counts[EntanglementFamily.QIA_A] > counts[EntanglementFamily.QIA_X]


def test_resource_accounting_is_stable_and_includes_declared_readout_options():
    config = QuantumAdapterConfig(
        q=3,
        R=2,
        L=2,
        encoding=EncodingSpec(trainable_scale=True),
        readout=ReadoutSpec(("Z0", "X2"), trainable_weights=True, trainable_bias=True),
        family="QIA-A",
    )

    expected = {
        "trainable_parameters": 2 * 3 * 3 + 3 + 2 + 1,
        "encoding_gates": 2 * 3 * 2,
        "one_qubit_gates": 2 * 3 * 2 + 2 * 3 * 3,
        "two_qubit_gates": 2 * 3,
        "logical_depth": 2 * 2 + 2 * (3 + 1),
        "observables": 2,
    }
    first = config.resources()
    second = config.resources()

    assert first == second
    assert first.to_dict() == expected
    assert config.to_json() == config.to_json()


def test_invalid_configurations_are_rejected():
    invalid = (
        lambda: QuantumAdapterConfig(q=0, R=1, L=1),
        lambda: QuantumAdapterConfig(q=2, R=0, L=1),
        lambda: QuantumAdapterConfig(q=2, R=1, L=1, family="QIA-Z"),
        lambda: EncodingSpec(rotations=()),
        lambda: ReadoutSpec(observables=()),
        lambda: QuantumAdapterConfig(q=2, R=1, L=1, readout=ReadoutSpec(("Z9",))),
        lambda: QuantumAdapterConfig(q=2, R=1, L=1, readout=ReadoutSpec(("Z2",))),
    )

    for constructor in invalid:
        with pytest.raises((TypeError, ValueError)):
            constructor()


def test_backend_neutral_placeholder_validates_parameter_shape_without_framework_imports():
    config = QuantumAdapterConfig(q=2, R=1, L=1)
    adapter = BackendNeutralAdapter(config)

    with pytest.raises(ValueError, match="expected 6 trainable parameters"):
        adapter.execute(np.zeros((1, 2)), np.zeros(5))
    with pytest.raises(NotImplementedError, match="backend-neutral"):
        adapter.execute(np.zeros((1, 2)), np.zeros(6), shots=10)
