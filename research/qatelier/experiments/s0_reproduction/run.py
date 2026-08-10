"""S0 execution gate and credential-free data-preparation entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from research.qatelier.experiments.s0_reproduction.prepare_data import prepare_s0


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
    parser.add_argument("--prepare", action="store_true", help="validate locks and prepare local S0 artifacts")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--encoder-path", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    document = yaml.safe_load(args.config.read_text())
    required_locks = tuple(path for path in REQUIRED_LOCKS if not (args.prepare and path == "artifacts.compressor_artifact"))
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
    raise SystemExit("S0 runner implementation is intentionally gated until the locked data loader is integrated")


if __name__ == "__main__":
    main()
