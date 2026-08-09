from pathlib import Path

from atelier.acceptance import run_acceptance


def test_offline_acceptance_smoke_passes():
    result = run_acceptance(Path(__file__).parents[1])
    assert result["status"] == "passed"
    assert len(result["checks"]) >= 12
