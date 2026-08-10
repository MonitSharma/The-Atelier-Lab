"""Build the committed deterministic SciFact query-selection manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np


ROOT = Path(__file__).resolve().parent
TRAIN_SEEDS = [11, 13, 17]
TRAIN_COUNTS = [32, 64, 128]
CONFIRMATION_SEEDS = [101, 103, 107, 109, 113]
CONFIRMATION_COUNT = 64


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ordered(values: Iterable[str]) -> list[str]:
    return sorted(set(values), key=lambda value: (int(value), value))


def _load_qrel_query_ids(path: Path) -> list[str]:
    with path.open(newline="") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    if not rows or set(rows[0]) != {"query-id", "corpus-id", "score"}:
        raise ValueError(f"unexpected qrels schema: {path}")
    if any(str(row["score"]) != "1" for row in rows):
        raise ValueError(f"SciFact qrels must contain only positive score 1: {path}")
    return _ordered(row["query-id"] for row in rows)


def _permutation(pool: list[str], seed: int, budget: int) -> list[str]:
    rng = np.random.Generator(np.random.PCG64(seed * 1000 + budget))
    order = rng.permutation(len(pool))
    return [pool[int(index)] for index in order]


def build(*, train_qrels: Path, test_qrels: Path, output: Path) -> Path:
    train_ids = _load_qrel_query_ids(train_qrels)
    test_ids = _load_qrel_query_ids(test_qrels)
    if set(train_ids).intersection(test_ids):
        raise ValueError("SciFact train and test qrels share query IDs")
    training: dict[str, dict[str, list[str]]] = {}
    for seed in TRAIN_SEEDS:
        permutation = _permutation(train_ids, seed, max(TRAIN_COUNTS))
        training[str(seed)] = {
            str(count): sorted(permutation[:count], key=lambda value: (int(value), value))
            for count in TRAIN_COUNTS
        }
    training_union = set().union(*(set(values[str(max(TRAIN_COUNTS))]) for values in training.values()))
    confirmation_pool = [query_id for query_id in train_ids if query_id not in training_union]
    if len(confirmation_pool) < CONFIRMATION_COUNT:
        raise ValueError("not enough train-qrels holdout queries for confirmation")
    confirmation = {
        str(seed): sorted(
            _permutation(confirmation_pool, seed, CONFIRMATION_COUNT)[:CONFIRMATION_COUNT],
            key=lambda value: (int(value), value),
        )
        for seed in CONFIRMATION_SEEDS
    }
    manifest = {
        "schema_version": 1,
        "task": "SciFact",
        "data_manifest_sha256": _sha256(ROOT / "data_manifest.json"),
        "selection_algorithm": "sorted numeric query IDs; numpy Generator(PCG64(seed * 1000 + budget)); take first n and sort",
        "training_source": "qrels/train.tsv",
        "confirmation_source": "qrels/train.tsv holdout after removing the union of all 128-query training selections",
        "test_source": "qrels/test.tsv",
        "training_selection_seeds": TRAIN_SEEDS,
        "training_query_counts": TRAIN_COUNTS,
        "confirmation_seeds": CONFIRMATION_SEEDS,
        "confirmation_query_count": CONFIRMATION_COUNT,
        "train_qrels_query_ids": train_ids,
        "test_qrels_query_ids": test_ids,
        "training_query_ids": training,
        "confirmation_query_ids": confirmation,
        "training_union_query_count": len(training_union),
        "confirmation_pool_query_count": len(confirmation_pool),
        "test_qrels_reserved": True,
        "test_tuning_allowed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-qrels", type=Path, required=True)
    parser.add_argument("--test-qrels", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "split_manifest.json")
    args = parser.parse_args()
    print(build(train_qrels=args.train_qrels, test_qrels=args.test_qrels, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
