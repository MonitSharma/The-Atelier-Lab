from __future__ import annotations

from types import SimpleNamespace

import pytest

from research.qatelier.hardware.ibm.preflight import (
    IBMPreflightError,
    backend_snapshot,
    credentials_available,
    require_frozen_candidate,
)


def test_credentials_are_reported_as_presence_only(tmp_path):
    env = tmp_path / ".env"
    env.write_text("QISKIT_IBM_TOKEN=secret-value\nQISKIT_IBM_INSTANCE=instance-value\n")
    report = credentials_available(env)
    assert report == {"credentials_available": True, "token_available": True, "instance_available": True}
    assert "secret-value" not in str(report)


def test_backend_snapshot_reads_status_without_submission():
    backend = SimpleNamespace(
        name="ibm_test",
        status=lambda: SimpleNamespace(operational=True, status_msg="active", pending_jobs=2),
        configuration=lambda: SimpleNamespace(num_qubits=5),
    )
    assert backend_snapshot(backend).to_dict() == {
        "name": "ibm_test", "operational": True, "status": "active", "pending_jobs": 2, "num_qubits": 5,
    }


def test_hardware_replay_requires_complete_frozen_panel():
    with pytest.raises(IBMPreflightError, match="frozen candidate panel"):
        require_frozen_candidate(None)
    with pytest.raises(IBMPreflightError, match="parameters_hash"):
        require_frozen_candidate({"model_hash": "m", "compressor_hash": "c", "sample_manifest_hash": "s", "circuit_hash": "q", "shots": 100, "observables": ["Z0"], "compilation_policy": "frozen"})
