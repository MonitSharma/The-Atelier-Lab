from __future__ import annotations

import json
from pathlib import Path

from research.qatelier.cli import main


def test_validate_reports_placeholders_without_executing(capsys):
    exit_code = main(["validate"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "execution_ready: false" in captured.out
    assert "$.representation.backbone.model_version" in captured.out
    assert "credentials" not in captured.out.lower()


def test_validate_structure_only_is_explicitly_non_executing(capsys):
    exit_code = main(["validate", "--structure-only", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    report = json.loads(captured.out)
    assert report["structurally_valid"] is True
    assert report["execution_ready"] is False


def test_toy_smoke_is_deterministic_and_writes_result(tmp_path: Path, capsys):
    output = tmp_path / "smoke.json"
    first_exit = main(
        ["smoke", "--seed", "11", "--train-size", "12", "--test-size", "20", "--output", str(output)]
    )
    first_stdout = capsys.readouterr().out
    first_file = output.read_text(encoding="utf-8")

    second_exit = main(
        ["smoke", "--seed", "11", "--train-size", "12", "--test-size", "20"]
    )
    second_stdout = capsys.readouterr().out

    assert first_exit == second_exit == 0
    assert first_stdout == first_file
    assert second_stdout == first_file
    payload = json.loads(first_file)
    assert payload["execution"] == {"provider": None, "backend": None, "credentials_used": False}
    assert payload["metrics"]["test_accuracy"] == 1.0


def test_smoke_with_protocol_config_fails_before_work(tmp_path: Path, capsys):
    output = tmp_path / "should-not-exist.json"

    exit_code = main(["smoke", "--config", str(Path("research/qatelier/config.yaml")), "--output", str(output)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "execution blocked" in captured.err
    assert not output.exists()


def test_reserved_execution_commands_are_explicit_and_fail_closed(capsys):
    exit_code = main(["quantum"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "execution blocked" in captured.err


def test_hardware_preflight_is_policy_only_and_credential_free(capsys):
    exit_code = main(["hardware-preflight", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["provider_contacted"] is False
    assert payload["jobs_submitted"] == 0
    assert payload["quantinuum_physical_jobs_allowed"] is False
