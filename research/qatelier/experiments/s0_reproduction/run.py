"""S0 execution gate placeholder; no result is claimed until locks are filled."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


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
    args = parser.parse_args()
    document = yaml.safe_load(args.config.read_text())
    missing = [path for path in REQUIRED_LOCKS if not _get(document, path)]
    if missing:
        raise SystemExit("S0 execution blocked; unresolved locks: " + ", ".join(missing))
    raise SystemExit("S0 runner implementation is intentionally gated until the locked data loader is integrated")


if __name__ == "__main__":
    main()
