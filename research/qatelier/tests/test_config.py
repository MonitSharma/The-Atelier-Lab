from __future__ import annotations

from pathlib import Path

import pytest

from research.qatelier.config import (
    UnresolvedScientificPlaceholderError,
    default_config_path,
    default_config_schema_path,
    find_unresolved_placeholders,
    load_execution_config,
    validate_config,
)


def test_committed_protocol_is_structurally_valid_but_not_execution_ready():
    report = validate_config()

    assert report.structurally_valid
    assert not report.execution_ready
    paths = {issue.path for issue in report.placeholder_issues}
    assert {
        "$.datasets.manifest",
        "$.representation.backbone.model_version",
        "$.representation.backbone.weights_digest",
        "$.representation.backbone.lock_state",
        "$.representation.preprocessing.normalization",
        "$.datasets.regimes[1].shift_definition",
        "$.seeds.split_seed",
        "$.hardware.backend_selection",
    } <= paths


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


def test_execution_loader_refuses_unresolved_protocol():
    with pytest.raises(UnresolvedScientificPlaceholderError, match="execution blocked"):
        load_execution_config()


def test_default_paths_are_shipped_files():
    assert Path(default_config_path()).is_file()
    assert Path(default_config_schema_path()).is_file()
