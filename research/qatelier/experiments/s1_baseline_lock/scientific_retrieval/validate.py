"""Validate the pinned S1 scientific-retrieval definition and split lock."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(name: str) -> dict[str, Any]:
    return json.loads((ROOT / name).read_text())


def _ordered_ids(ids: list[str]) -> list[str]:
    return sorted(ids, key=lambda value: (int(value), value))


def _permutation(pool: list[str], seed: int, budget: int) -> list[str]:
    rng = np.random.Generator(np.random.PCG64(seed * 1000 + budget))
    order = rng.permutation(len(pool))
    return [pool[int(index)] for index in order]


def _expected_training(pool: list[str], seeds: list[int], counts: list[int]) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}
    for seed in seeds:
        permutation = _permutation(pool, seed, max(counts))
        result[str(seed)] = {str(count): _ordered_ids(permutation[:count]) for count in counts}
    return result


def _expected_confirmation(pool: list[str], seeds: list[int], count: int) -> dict[str, list[str]]:
    return {str(seed): _ordered_ids(_permutation(pool, seed, count)[:count]) for seed in seeds}


def _validate_static() -> dict[str, Any]:
    config = yaml_safe_load(ROOT / "config.yaml")
    data = _load("data_manifest.json")
    split = _load("split_manifest.json")
    assert config["status"] == "reference_definition_ready"
    assert config["protocol"]["test_tuning_allowed"] is False
    assert config["protocol"]["quantum_provider_contacted"] is False
    assert config["protocol"]["hardware_jobs_submitted"] == 0
    assert split["data_manifest_sha256"] == _sha256(ROOT / "data_manifest.json")
    assert split["test_qrels_reserved"] is True
    for member in data["members"].values():
        assert len(member["sha256"]) == 64 and all(character in "0123456789abcdef" for character in member["sha256"])
        assert member["rows"] > 0
        assert "url" in member
    train_ids = _ordered_ids(split["train_qrels_query_ids"])
    training = _expected_training(
        train_ids,
        split["training_selection_seeds"],
        split["training_query_counts"],
    )
    assert training == split["training_query_ids"]
    training_union = set().union(*(set(values[str(max(split["training_query_counts"]))]) for values in training.values()))
    confirmation_pool = [query_id for query_id in train_ids if query_id not in training_union]
    assert len(confirmation_pool) >= split["confirmation_query_count"]
    confirmation = _expected_confirmation(confirmation_pool, split["confirmation_seeds"], split["confirmation_query_count"])
    assert confirmation == split["confirmation_query_ids"]
    assert not training_union.intersection(*(set(values) for values in confirmation.values()))
    assert len(training_union) == split["training_union_query_count"]
    assert len(confirmation_pool) == split["confirmation_pool_query_count"]
    assert set(split["test_qrels_query_ids"]).isdisjoint(set(train_ids))
    return {
        "status": "valid",
        "task": config["task"]["name"],
        "train_qrels_query_count": len(train_ids),
        "training_union_query_count": len(training_union),
        "confirmation_pool_query_count": len(confirmation_pool),
        "confirmation_seed_count": len(confirmation),
        "test_qrels_query_count": len(split["test_qrels_query_ids"]),
        "quantum_provider_contacted": False,
        "hardware_jobs_submitted": 0,
    }


def yaml_safe_load(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("validation requires PyYAML") from exc
    return yaml.safe_load(path.read_text())


def _validate_data(data_dir: Path) -> dict[str, Any]:
    data = _load("data_manifest.json")
    checked = []
    parquet_ids: dict[str, set[str]] = {}
    for member_name, member in data["members"].items():
        path = data_dir / member["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        if actual != member["sha256"]:
            raise ValueError(f"{member_name} hash mismatch: {actual} != {member['sha256']}")
        if member_name in {"corpus", "queries"}:
            try:
                import pyarrow.parquet as parquet
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("data validation requires pyarrow") from exc
            table = parquet.read_table(path)
            if table.num_rows != member["rows"] or table.column_names != member["columns"]:
                raise ValueError(f"{member_name} parquet schema/count mismatch")
            ids = [str(value) for value in table[member["id_column"]].to_pylist()]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{member_name} contains duplicate IDs")
            parquet_ids[member_name] = set(ids)
        else:
            with path.open(newline="") as source:
                rows = list(csv.DictReader(source, delimiter="\t"))
            if len(rows) != member["rows"]:
                raise ValueError(f"{member_name} qrels row count mismatch")
            if not rows or list(rows[0]) != member["columns"]:
                raise ValueError(f"{member_name} qrels schema mismatch")
            if any(str(row["score"]) not in {str(value) for value in member["positive_scores"]} for row in rows):
                raise ValueError(f"{member_name} contains an unexpected relevance score")
            if len({row["query-id"] for row in rows}) != member["query_count"]:
                raise ValueError(f"{member_name} qrels query count mismatch")
            if "corpus" in parquet_ids and any(row["corpus-id"] not in parquet_ids["corpus"] for row in rows):
                raise ValueError(f"{member_name} references a corpus ID outside the pinned corpus")
            if "queries" in parquet_ids and any(row["query-id"] not in parquet_ids["queries"] for row in rows):
                raise ValueError(f"{member_name} references a query ID outside the pinned queries")
        checked.append(member_name)
    train_path = data_dir / data["members"]["qrels_train"]["path"]
    test_path = data_dir / data["members"]["qrels_test"]["path"]
    with train_path.open(newline="") as source:
        train_ids = {row["query-id"] for row in csv.DictReader(source, delimiter="\t")}
    with test_path.open(newline="") as source:
        test_ids = {row["query-id"] for row in csv.DictReader(source, delimiter="\t")}
    if train_ids.intersection(test_ids):
        raise ValueError("downloaded SciFact train/test qrels overlap")
    return {"data_files_checked": checked}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="Optional directory containing paths from data_manifest.json")
    args = parser.parse_args()
    report = _validate_static()
    if args.data_dir is not None:
        report.update(_validate_data(args.data_dir))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
