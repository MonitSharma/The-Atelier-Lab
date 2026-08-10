"""Generate and validate the S1 controlled interaction-order data artifact.

This module deliberately has no quantum or provider imports. It uses the
canonical QAtelier benchmark so that the shared-target and fixed-threshold
semantics are identical to the later mechanism screen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from research.qatelier.benchmark import make_interaction_problem


ROOT = Path(__file__).resolve().parent
DATA_RELATIVE = Path("data/controlled_interaction_order.npz")
MANIFEST_RELATIVE = Path("manifest.json")
VALIDATION_RELATIVE = Path("validation.json")

N_FEATURES = 6
ORDERS = (1, 2, 3, 4, 5, 6)
FAMILIES = (
    ("aligned_polynomial", "aligned", 0),
    ("rotated_polynomial", "rotated", 1),
    ("misaligned_dense", "misaligned", 2),
    ("fourier_trigonometric", "fourier", 3),
)
TRAIN_SEEDS = (11, 13, 17)
CONFIRMATION_SEEDS = (101, 103, 107, 109, 113)
BUDGETS_PER_CLASS = (16, 32, 64, 128, 256)
MAX_PER_CLASS = 256
BLOCK_SIZE = 4096
PROBLEM_SEED_BASE = 314159
BLOCK_SEED_STRIDE = 1_000_003


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_ready(item) for item in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def _array_hashes(arrays: dict[str, np.ndarray]) -> dict[str, str]:
    """Hash arrays with dtype and shape so serialization cannot hide drift."""
    hashes: dict[str, str] = {}
    for name, array in arrays.items():
        value = np.ascontiguousarray(array)
        digest = hashlib.sha256()
        digest.update(str(value.dtype).encode("utf-8"))
        digest.update(repr(value.shape).encode("utf-8"))
        digest.update(value.tobytes())
        hashes[name] = digest.hexdigest()
    return hashes


def _bundle_hash(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name in arrays:
        digest.update(name.encode("utf-8"))
        digest.update(bytes.fromhex(_array_hashes({name: arrays[name]})[name]))
    return digest.hexdigest()


def _problem_seed(order: int, family_index: int) -> int:
    return PROBLEM_SEED_BASE + 100 * order + family_index


def _balanced_split(problem: Any, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int]]:
    """Collect exactly MAX_PER_CLASS rows per class from deterministic blocks."""
    by_class: dict[int, list[np.ndarray]] = {0: [], 1: []}
    source_indices: dict[int, list[int]] = {0: [], 1: []}
    counts = {0: 0, 1: 0}
    block_index = 0
    while min(counts.values()) < MAX_PER_CLASS:
        block_seed = seed + BLOCK_SEED_STRIDE * block_index
        block = problem.sample(BLOCK_SIZE, seed=block_seed)
        for label in (0, 1):
            remaining = MAX_PER_CLASS - counts[label]
            if remaining <= 0:
                continue
            positions = np.flatnonzero(block.labels == label)[:remaining]
            by_class[label].append(block.features[positions])
            source_indices[label].extend(
                (block_index * BLOCK_SIZE + int(position)) for position in positions
            )
            counts[label] += int(positions.size)
        block_index += 1

    features = np.concatenate((np.concatenate(by_class[0]), np.concatenate(by_class[1])))
    labels = np.concatenate(
        (
            np.zeros(MAX_PER_CLASS, dtype=np.int8),
            np.ones(MAX_PER_CLASS, dtype=np.int8),
        )
    )
    indices = np.asarray(source_indices[0] + source_indices[1], dtype=np.int64)
    return features, labels, indices, [seed + BLOCK_SEED_STRIDE * i for i in range(block_index)]


def _split_fingerprint(features: np.ndarray, labels: np.ndarray, source_indices: np.ndarray) -> str:
    return _bundle_hash({"features": features, "labels": labels, "source_indices": source_indices})


def _budget_indices(budget: int) -> list[int]:
    return list(range(budget)) + list(range(MAX_PER_CLASS, MAX_PER_CLASS + budget))


def _build_artifact() -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    feature_rows: list[np.ndarray] = []
    label_rows: list[np.ndarray] = []
    source_rows: list[np.ndarray] = []
    orders: list[int] = []
    family_indices: list[int] = []
    seeds: list[int] = []
    kinds: list[str] = []
    split_records: list[dict[str, Any]] = []
    problem_records: list[dict[str, Any]] = []
    data_index = 0

    for family_name, canonical_family, family_index in FAMILIES:
        for order in ORDERS:
            problem = make_interaction_problem(
                n_features=N_FEATURES,
                order=order,
                family=canonical_family,
                problem_seed=_problem_seed(order, family_index),
                threshold=0.0,
                observation_noise_std=0.0,
                label_noise=0.0,
            )
            problem_records.append(
                {
                    "problem_id": f"{family_name}-order-{order}",
                    "family": family_name,
                    "canonical_family": canonical_family,
                    "family_index": family_index,
                    "order": order,
                    "problem_seed": _problem_seed(order, family_index),
                    "target_fingerprint": problem.target_fingerprint,
                    "target_definition": _json_ready(problem.target_definition),
                    "threshold": 0.0,
                    "threshold_source": problem.threshold_source,
                }
            )
            for kind, split_seeds in (("train", TRAIN_SEEDS), ("confirmation", CONFIRMATION_SEEDS)):
                for seed in split_seeds:
                    features, labels, source_indices, block_seeds = _balanced_split(problem, seed)
                    feature_rows.append(features)
                    label_rows.append(labels)
                    source_rows.append(source_indices)
                    orders.append(order)
                    family_indices.append(family_index)
                    seeds.append(seed)
                    kinds.append(kind)
                    split_records.append(
                        {
                            "split_id": f"{family_name}-order-{order}-{kind}-{seed}",
                            "problem_id": f"{family_name}-order-{order}",
                            "family": family_name,
                            "canonical_family": canonical_family,
                            "order": order,
                            "kind": kind,
                            "seed": seed,
                            "data_index": data_index,
                            "n_rows": int(features.shape[0]),
                            "n_features": int(features.shape[1]),
                            "class_counts": {"0": MAX_PER_CLASS, "1": MAX_PER_CLASS},
                            "candidate_block_seeds": block_seeds,
                            "source_indices_hash": _array_hashes({"source_indices": source_indices})[
                                "source_indices"
                            ],
                            "split_fingerprint": _split_fingerprint(features, labels, source_indices),
                            "budget_selection_indices": {
                                str(budget): _budget_indices(budget)
                                for budget in BUDGETS_PER_CLASS
                            }
                            if kind == "train"
                            else None,
                        }
                    )
                    data_index += 1

    arrays = {
        "features": np.stack(feature_rows).astype(np.float64, copy=False),
        "labels": np.stack(label_rows).astype(np.int8, copy=False),
        "source_indices": np.stack(source_rows).astype(np.int64, copy=False),
        "orders": np.asarray(orders, dtype=np.int8),
        "family_indices": np.asarray(family_indices, dtype=np.int8),
        "seeds": np.asarray(seeds, dtype=np.int64),
        "kinds": np.asarray(kinds),
    }
    manifest = {
        "schema_version": 1,
        "artifact_id": "qatelier-s1-controlled-interaction-order",
        "status": "generated_reproducible_definition",
        "generator": {
            "module": "research.qatelier.benchmark.make_interaction_problem",
            "script": "generate.py",
            "algorithm": "numpy.PCG64; deterministic balanced block collection",
            "block_seed_stride": BLOCK_SEED_STRIDE,
            "numpy_version_at_generation": np.__version__,
        },
        "feature_space": {
            "n_features": N_FEATURES,
            "distribution": "standard_normal",
            "observation_noise_std": 0.0,
            "label_noise": 0.0,
            "threshold": 0.0,
            "label_rule": "1 if latent_score >= threshold, otherwise 0",
        },
        "orders": list(ORDERS),
        "families": [
            {
                "name": name,
                "canonical_family": canonical,
                "family_index": index,
            }
            for name, canonical, index in FAMILIES
        ],
        "split_protocol": {
            "train_selection_seeds": list(TRAIN_SEEDS),
            "confirmation_seeds": list(CONFIRMATION_SEEDS),
            "budgets_per_class": list(BUDGETS_PER_CLASS),
            "max_rows_per_class": MAX_PER_CLASS,
            "sampling_block_size": BLOCK_SIZE,
            "threshold_is_frozen_before_sampling": True,
            "confirmation_is_never_used_for_fitting_or_selection": True,
        },
        "problems": problem_records,
        "splits": split_records,
        "data": {
            "path": str(DATA_RELATIVE),
            "array_order": list(arrays),
            "array_shapes": {name: list(value.shape) for name, value in arrays.items()},
            "array_hashes": _array_hashes(arrays),
            "bundle_hash": _bundle_hash(arrays),
        },
        "provider_safety": {"providers_contacted": False, "jobs_submitted": 0},
    }
    return arrays, manifest


def write_artifact(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = output_dir / DATA_RELATIVE
    data_path.parent.mkdir(parents=True, exist_ok=True)
    arrays, manifest = _build_artifact()
    np.savez_compressed(data_path, **arrays)
    manifest["generator"]["script_sha256"] = _sha256_file(Path(__file__))
    manifest["data"]["file_sha256"] = _sha256_file(data_path)
    manifest_path = output_dir / MANIFEST_RELATIVE
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = validate_artifact(output_dir, expected_manifest=manifest)
    (output_dir / VALIDATION_RELATIVE).write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return validation


def validate_artifact(output_dir: Path, *, expected_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest_path = output_dir / MANIFEST_RELATIVE
    data_path = output_dir / DATA_RELATIVE
    if expected_manifest is None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = expected_manifest
    with np.load(data_path, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in manifest["data"]["array_order"]}

    actual_hashes = _array_hashes(arrays)
    if actual_hashes != manifest["data"]["array_hashes"]:
        raise ValueError("controlled-order array hashes do not match manifest")
    if _bundle_hash(arrays) != manifest["data"]["bundle_hash"]:
        raise ValueError("controlled-order bundle hash does not match manifest")
    if len(manifest["problems"]) != len(ORDERS) * len(FAMILIES):
        raise ValueError("manifest must contain one problem for every family/order pair")
    if len(manifest["splits"]) != len(ORDERS) * len(FAMILIES) * (len(TRAIN_SEEDS) + len(CONFIRMATION_SEEDS)):
        raise ValueError("manifest split count is not the declared train/confirmation matrix")

    problems = {
        record["problem_id"]: make_interaction_problem(
            n_features=N_FEATURES,
            order=int(record["order"]),
            family=record["canonical_family"],
            problem_seed=int(record["problem_seed"]),
            threshold=0.0,
            observation_noise_std=0.0,
            label_noise=0.0,
        )
        for record in manifest["problems"]
    }
    split_fingerprints: list[str] = []
    for record in manifest["splits"]:
        index = int(record["data_index"])
        features = arrays["features"][index]
        labels = arrays["labels"][index]
        source_indices = arrays["source_indices"][index]
        if features.shape != (2 * MAX_PER_CLASS, N_FEATURES):
            raise ValueError(f"wrong feature shape for {record['split_id']}")
        if not np.array_equal(labels, np.concatenate((np.zeros(MAX_PER_CLASS, dtype=np.int8), np.ones(MAX_PER_CLASS, dtype=np.int8)))):
            raise ValueError(f"class rows are not canonical for {record['split_id']}")
        problem = problems[record["problem_id"]]
        if problem.target_fingerprint != next(
            item["target_fingerprint"]
            for item in manifest["problems"]
            if item["problem_id"] == record["problem_id"]
        ):
            raise ValueError(f"target fingerprint mismatch for {record['problem_id']}")
        expected_labels = (problem.score(features) >= 0.0).astype(np.int8)
        if not np.array_equal(labels, expected_labels):
            raise ValueError(f"labels do not follow the frozen target for {record['split_id']}")
        if _split_fingerprint(features, labels, source_indices) != record["split_fingerprint"]:
            raise ValueError(f"split fingerprint mismatch for {record['split_id']}")
        split_fingerprints.append(record["split_fingerprint"])
    if len(set(split_fingerprints)) != len(split_fingerprints):
        raise ValueError("train/confirmation split fingerprints are not unique")

    return {
        "schema_version": 1,
        "artifact_id": manifest["artifact_id"],
        "status": "validated",
        "data_file": str(DATA_RELATIVE),
        "data_file_sha256": _sha256_file(data_path),
        "array_bundle_hash": manifest["data"]["bundle_hash"],
        "problem_count": len(manifest["problems"]),
        "split_count": len(manifest["splits"]),
        "orders": list(ORDERS),
        "families": [name for name, _, _ in FAMILIES],
        "train_selection_count": len(TRAIN_SEEDS),
        "confirmation_count": len(CONFIRMATION_SEEDS),
        "providers_contacted": False,
        "jobs_submitted": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output-dir", type=Path, help="write a fresh artifact here")
    group.add_argument("--check-dir", type=Path, help="validate an existing artifact")
    args = parser.parse_args()
    if args.output_dir is not None:
        validation = write_artifact(args.output_dir)
    else:
        validation = validate_artifact(args.check_dir)
    print(json.dumps(validation, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
