"""Explicit, credential-free command line entry point for QAtelier P0.

Examples
--------
Inspect the committed protocol (this reports unresolved fields):

    python -m research.qatelier.cli validate

Run the deterministic local smoke path without a model, provider, or secret:

    python -m research.qatelier.cli smoke --output /tmp/qatelier-smoke.json

The smoke path is deliberately a toy validation, not a scientific result and
not a quantum execution.  Commands that would eventually consume a scientific
config are explicit and fail closed until their implementation and protocol
gates exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .config import (
    ConfigurationError,
    ConfigValidationReport,
    UnresolvedScientificPlaceholderError,
    default_config_path,
    default_config_schema_path,
    load_execution_config,
    validate_config,
)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qatelier",
        description="Local QAtelier research infrastructure (P0).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="validate protocol structure and execution readiness"
    )
    validate_parser.add_argument(
        "--config", type=Path, default=default_config_path(), help="YAML protocol path"
    )
    validate_parser.add_argument(
        "--schema", type=Path, default=default_config_schema_path(), help="JSON schema path"
    )
    validate_parser.add_argument(
        "--json", action="store_true", help="emit a machine-readable report"
    )
    validate_parser.add_argument(
        "--structure-only",
        action="store_true",
        help="allow unresolved planning markers in the report (never enables execution)",
    )

    smoke_parser = subparsers.add_parser(
        "smoke", help="run a deterministic credential-free toy validation"
    )
    smoke_parser.add_argument("--seed", type=_non_negative_int, default=7)
    smoke_parser.add_argument("--train-size", type=_positive_int, default=16)
    smoke_parser.add_argument("--test-size", type=_positive_int, default=16)
    smoke_parser.add_argument("--features", type=_positive_int, default=2)
    smoke_parser.add_argument(
        "--output", type=Path, help="write the deterministic result JSON to this path"
    )
    smoke_parser.add_argument(
        "--config",
        type=Path,
        help="optional protocol config; unresolved fields block the smoke command",
    )

    for name, help_text in (
        ("prepare-data", "reserved data-preparation command"),
        ("baseline", "reserved classical-baseline command"),
        ("quantum", "reserved quantum execution command"),
        ("analyze", "reserved analysis command"),
        ("paper", "reserved manuscript packaging command"),
        ("audit", "reserved reproducibility audit command"),
        ("reproduce", "reserved credential-free reproduction command"),
        ("hardware-preflight", "reserved provider preflight command"),
    ):
        stage_parser = subparsers.add_parser(name, help=help_text)
        stage_parser.add_argument(
            "--config", type=Path, default=default_config_path(), help="YAML protocol path"
        )
        stage_parser.add_argument(
            "--schema", type=Path, default=default_config_schema_path(), help="JSON schema path"
        )
        if name == "hardware-preflight":
            stage_parser.add_argument(
                "--json", action="store_true", dest="as_json",
                help="report the locked provider policy without contacting a backend",
            )

    return parser


def _report_text(report: ConfigValidationReport) -> str:
    lines = [
        f"config: {report.path}",
        f"schema: {report.schema_path}",
        f"structurally_valid: {str(report.structurally_valid).lower()}",
        f"execution_ready: {str(report.execution_ready).lower()}",
    ]
    if report.schema_errors:
        lines.append("schema_errors:")
        lines.extend(f"  - {error}" for error in report.schema_errors)
    if report.placeholder_issues:
        lines.append("unresolved_placeholders:")
        lines.extend(
            f"  - {issue.path}: {issue.value!r} ({issue.reason})"
            for issue in report.placeholder_issues
        )
    return "\n".join(lines)


def _run_validate(args: argparse.Namespace) -> int:
    report = validate_config(args.config, schema_path=args.schema)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True) if args.json else _report_text(report))
    if report.schema_errors:
        return 2
    # Validation is an inspection command, not an execution command.  A
    # structurally valid planning config may intentionally be unresolved; the
    # report makes that state explicit and execution paths enforce the gate.
    return 0


def _toy_payload(*, seed: int, train_size: int, test_size: int, features: int) -> dict[str, Any]:
    """Create a tiny deterministic end-to-end artifact without provider access."""

    import numpy as np

    if features < 2:
        raise ConfigurationError("toy smoke requires at least two features")
    rng = np.random.Generator(np.random.PCG64(seed))
    train_x = rng.standard_normal((train_size, features))
    test_x = rng.standard_normal((test_size, features))

    def target(values: np.ndarray) -> np.ndarray:
        return (values[:, 0] * values[:, 1] >= 0).astype(np.int8)

    train_y = target(train_x)
    test_y = target(test_x)
    predictions = target(test_x)
    accuracy = float(np.mean(predictions == test_y))

    def digest(*arrays: np.ndarray) -> str:
        hasher = hashlib.sha256()
        for array in arrays:
            hasher.update(str(array.dtype).encode("ascii"))
            hasher.update(repr(array.shape).encode("ascii"))
            hasher.update(array.tobytes(order="C"))
        return hasher.hexdigest()

    return {
        "schema_version": 1,
        "experiment_id": "qatelier-deterministic-toy-smoke",
        "mode": "toy_validation",
        "execution": {"provider": None, "backend": None, "credentials_used": False},
        "seed": seed,
        "data": {
            "train_size": train_size,
            "test_size": test_size,
            "features": features,
            "target": "sign(x[0] * x[1])",
            "data_digest": digest(train_x, train_y, test_x, test_y),
        },
        "model": {"name": "deterministic_product_rule", "trainable_parameters": 0},
        "metrics": {"test_accuracy": accuracy},
        "reproduction": {
            "command": (
                "python -m research.qatelier.cli smoke "
                f"--seed {seed} --train-size {train_size} --test-size {test_size} "
                f"--features {features}"
            ),
            "deterministic": True,
        },
        "notes": [
            "Toy infrastructure validation only; no scientific claim.",
            "No quantum SDK, provider credential, or remote job was used.",
        ],
    }


def _run_smoke(args: argparse.Namespace) -> int:
    if args.config is not None:
        # Deliberately load through the execution gate before doing any work.
        load_execution_config(args.config)
    payload = _toy_payload(
        seed=args.seed,
        train_size=args.train_size,
        test_size=args.test_size,
        features=args.features,
    )
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


def _run_reserved_stage(args: argparse.Namespace) -> int:
    # Validate first, so a future stage cannot accidentally bypass the safety
    # gate merely because its implementation is added later.
    load_execution_config(args.config, schema_path=args.schema)
    raise ConfigurationError(
        f"{args.command} is not implemented in P0; no experiment was executed"
    )


def _run_hardware_preflight(args: argparse.Namespace) -> int:
    """Report the non-submitting hardware policy without scientific locks."""

    report = validate_config(args.config, schema_path=args.schema)
    payload = {
        "config_path": str(report.path),
        "config_structurally_valid": report.structurally_valid,
        "ibm_physical_execution": "gated_until_frozen_candidate",
        "quantinuum_physical_jobs_allowed": False,
        "quantinuum_allowed_backend": "Helios-1E",
        "quantinuum_syntax_check_required": True,
        "quantinuum_cost_check_required": True,
        "provider_contacted": False,
        "jobs_submitted": 0,
    }
    if args.as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_report_text(report))
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.structurally_valid else 2


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            return _run_validate(args)
        if args.command == "smoke":
            return _run_smoke(args)
        if args.command == "hardware-preflight" and getattr(args, "as_json", False):
            return _run_hardware_preflight(args)
        return _run_reserved_stage(args)
    except (ConfigurationError, UnresolvedScientificPlaceholderError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["main"]
