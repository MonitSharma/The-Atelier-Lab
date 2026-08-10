from __future__ import annotations

import json

import pytest

from research.qatelier.hardware.policy import (
    HELIOS_1E_EMULATOR,
    HardwarePolicyError,
    QuantinuumPolicy,
)
from research.qatelier.hardware.quantinuum.cost import CostCheckManifest, validate_cost_manifest
from research.qatelier.hardware.quantinuum.discovery import DeviceRecord, require_helios_1e_identifier


def _manifest(tmp_path, **updates):
    payload = {
        "logical_circuit_hash": "logical",
        "compiled_circuit_hash": "compiled",
        "configuration_hash": "config",
        "backend": HELIOS_1E_EMULATOR,
        "checker_backend": HELIOS_1E_EMULATOR,
        "syntax_checker_result": "accepted",
        "estimated_HQC_cost": 0.25,
        "checker_timestamp": "2026-08-10T00:00:00Z",
        "qubits": 2,
        "shots": 1000,
        "logical_1q_gates": 4,
        "logical_2q_gates": 1,
        "compiled_1q_gates": 5,
        "compiled_2q_gates": 1,
        "compiled_depth": 4,
        "measurement_count": 1,
        "requested_repetitions": 1,
        "software_versions": {"qatelier": "test"},
        "physical_hardware_allowed": False,
    }
    payload.update(updates)
    path = tmp_path / "cost.json"
    path.write_text(json.dumps(payload))
    return path


def test_physical_quantinuum_execution_is_always_rejected(tmp_path):
    policy = QuantinuumPolicy()
    with pytest.raises(HardwarePolicyError, match="physical execution is disabled"):
        policy.validate_submission(
            backend=HELIOS_1E_EMULATOR,
            physical_execution=True,
            cost_manifest=_manifest(tmp_path),
            logical_circuit_hash="logical",
            configuration_hash="config",
        )


def test_only_exact_helios_emulator_and_matching_cost_manifest_are_allowed(tmp_path):
    policy = QuantinuumPolicy()
    with pytest.raises(HardwarePolicyError, match="only Helios-1E"):
        policy.validate_submission(
            backend="Helios-1",
            physical_execution=False,
            cost_manifest=_manifest(tmp_path),
            logical_circuit_hash="logical",
            configuration_hash="config",
        )
    assert policy.validate_submission(
        backend=HELIOS_1E_EMULATOR,
        physical_execution=False,
        cost_manifest=_manifest(tmp_path),
        logical_circuit_hash="logical",
        configuration_hash="config",
    )["physical_execution"] is False


def test_missing_or_mismatched_cost_check_blocks_execution(tmp_path):
    policy = QuantinuumPolicy()
    with pytest.raises(HardwarePolicyError, match="cost check required"):
        policy.validate_submission(
            backend=HELIOS_1E_EMULATOR,
            physical_execution=False,
            cost_manifest=None,
            logical_circuit_hash="logical",
            configuration_hash="config",
        )
    with pytest.raises(HardwarePolicyError, match="exact logical circuit"):
        policy.validate_submission(
            backend=HELIOS_1E_EMULATOR,
            physical_execution=False,
            cost_manifest=_manifest(tmp_path),
            logical_circuit_hash="other",
            configuration_hash="config",
        )


def test_cost_manifest_is_immutable_and_preserves_estimate_vs_actual(tmp_path):
    manifest = CostCheckManifest(
        experiment_id="s5",
        candidate_id="qia-l",
        logical_circuit_hash="logical",
        compiled_circuit_hash="compiled",
        configuration_hash="config",
        qubits=2,
        shots=1000,
        logical_1q_gates=4,
        logical_2q_gates=1,
        compiled_1q_gates=5,
        compiled_2q_gates=1,
        compiled_depth=4,
        measurement_count=1,
        requested_repetitions=1,
        estimated_HQC_cost=0.25,
        checker_timestamp="2026-08-10T00:00:00Z",
        actual_hqc_cost=0.30,
    )
    path = manifest.write_json(tmp_path / "cost.json")
    assert validate_cost_manifest(path, logical_circuit_hash="logical", configuration_hash="config").actual_hqc_cost == 0.30
    with pytest.raises(FileExistsError):
        manifest.write_json(path)


def test_device_discovery_requires_exact_helios_1e_provider_identifier():
    records = (
        DeviceRecord("Helios-1E", "Quantinuum", False, "emulator", 98),
    )
    assert require_helios_1e_identifier(records).device_name == "Helios-1E"
    with pytest.raises(HardwarePolicyError, match="exactly one"):
        require_helios_1e_identifier(())
