from __future__ import annotations

from pathlib import Path

from research.qatelier.config import (
    default_config_path,
    default_config_schema_path,
    find_unresolved_placeholders,
    load_execution_config,
    validate_config,
)


def test_committed_protocol_is_structurally_and_execution_ready():
    report = validate_config()

    assert report.structurally_valid
    assert report.execution_ready
    assert not report.placeholder_issues


def test_placeholder_scan_is_deterministic_and_does_not_flag_protocol_language():
    document = {
        "safe": "training_split_only",
        "nested": ["record_dataset_manifest_and_version_before_run", "TBD"],
    }

    issues = find_unresolved_placeholders(document)

    assert [(issue.path, issue.reason) for issue in issues] == [
        ("$.nested[0]", "record-before-run marker"),
        ("$.nested[1]", "placeholder marker"),
    ]


def test_execution_loader_accepts_the_locked_negative_phase_protocol():
    document = load_execution_config()
    assert document["hardware"]["backend_selection"] == "none_authorized_no_candidate_frozen"


def test_default_paths_are_shipped_files():
    assert Path(default_config_path()).is_file()
    assert Path(default_config_schema_path()).is_file()
