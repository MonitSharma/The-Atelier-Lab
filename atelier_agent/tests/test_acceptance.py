from pathlib import Path

from atelier.acceptance import run_acceptance, run_clean_acceptance


def test_offline_acceptance_smoke_passes():
    result = run_acceptance(Path(__file__).parents[1])
    assert result["status"] == "passed"
    assert len(result["checks"]) >= 12


def test_clean_model_free_acceptance_restarts_and_resumes_state():
    result = run_clean_acceptance(Path(__file__).parents[1])
    assert result["status"] == "passed"
    assert result["mode"] == "clean_model_free"
    assert {check["name"] for check in result["checks"]} >= {
        "clean-restart-state", "clean-paper-complete", "clean-local-only",
    }
