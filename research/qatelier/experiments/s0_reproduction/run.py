"""S0 execution gate and credential-free data-preparation entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from research.qatelier.experiments.s0_reproduction.prepare_data import prepare_s0
from research.qatelier.experiments.s0_reproduction.execution import run_s0


REQUIRED_LOCKS = (
    "encoder.revision",
    "encoder.weights_digest",
    "dataset.version",
    "dataset.split_manifest",
    "representation.normalization",
    "artifacts.embedding_manifest",
    "artifacts.compressor_artifact",
)


def _get(document: dict, path: str):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true", help="validate locks and prepare local S0 artifacts")
    mode.add_argument("--run", action="store_true", help="run the fixed classical and simulator S0 panel")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--encoder-path", type=Path)
    parser.add_argument("--prepared-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--selection-limit", type=int)
    parser.add_argument("--candidate-limit", type=int)
    args = parser.parse_args()
    document = yaml.safe_load(args.config.read_text())
    required_locks = tuple(
        path for path in REQUIRED_LOCKS
        if not ((args.prepare or args.run) and path == "artifacts.compressor_artifact")
    )
    missing = [path for path in required_locks if not _get(document, path)]
    if missing:
        raise SystemExit("S0 execution blocked; unresolved locks: " + ", ".join(missing))
    if args.prepare:
        missing_args = [name for name, value in (("--archive", args.archive), ("--encoder-path", args.encoder_path), ("--output-dir", args.output_dir)) if value is None]
        if missing_args:
            raise SystemExit("S0 preparation requires: " + ", ".join(missing_args))
        destination = prepare_s0(
            config_path=args.config,
            archive_path=args.archive,
            encoder_path=args.encoder_path,
            output_dir=args.output_dir,
        )
        print(f"S0 preparation complete: {destination}")
        return 0
    if args.run:
        missing_args = [
            name
            for name, value in (("--prepared-dir", args.prepared_dir), ("--output-dir", args.output_dir))
            if value is None
        ]
        if missing_args:
            raise SystemExit("S0 execution requires: " + ", ".join(missing_args))
        destination = run_s0(
            config_path=args.config,
            prepared_dir=args.prepared_dir,
            output_dir=args.output_dir,
            selection_limit=args.selection_limit,
            candidate_limit=args.candidate_limit,
        )
        print(f"S0 execution complete: {destination}")
        return 0
    raise SystemExit("S0 runner implementation is intentionally gated until the locked data loader is integrated")


if __name__ == "__main__":
    main()
