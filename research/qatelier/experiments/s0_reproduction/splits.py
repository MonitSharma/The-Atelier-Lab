"""Validated, deterministic SST-2 selections for the S0 protocol."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
import zipfile

import numpy as np


LABELS = ("0", "1")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sentence_sample_id(source_member: str, row_index: int, sentence: str) -> str:
    digest = sha256_bytes(sentence.encode("utf-8"))[:12]
    return f"sst2-{source_member}-{row_index}-{digest}"


def read_tsv_member(
    archive_path: str | Path,
    member: str,
    *,
    expected_sha256: str,
) -> list[dict[str, str]]:
    """Read and hash one official SST-2 archive member."""

    archive = Path(archive_path)
    if not archive.is_file():
        raise FileNotFoundError(f"SST-2 archive does not exist: {archive}")
    with zipfile.ZipFile(archive) as source:
        try:
            payload = source.read(member)
        except KeyError as exc:
            raise ValueError(f"SST-2 archive is missing member: {member}") from exc
    actual = sha256_bytes(payload)
    if actual != expected_sha256:
        raise ValueError(f"SST-2 member hash mismatch for {member}: {actual} != {expected_sha256}")
    rows = list(csv.DictReader(payload.decode("utf-8").splitlines(), delimiter="\t"))
    if not rows or "sentence" not in rows[0]:
        raise ValueError(f"SST-2 member has no sentence column: {member}")
    return rows


def select_stratified_indices(rows: list[dict[str, str]], *, seed: int, budget_per_class: int) -> list[int]:
    """Recreate the preregistered PCG64 stratified selection exactly."""

    if budget_per_class < 1:
        raise ValueError("budget_per_class must be positive")
    rng = np.random.Generator(np.random.PCG64(seed * 1000 + budget_per_class))
    selected: list[int] = []
    for label in LABELS:
        pool = np.asarray([index for index, row in enumerate(rows) if row.get("label") == label], dtype=np.int64)
        if len(pool) < budget_per_class:
            raise ValueError(f"not enough rows for label {label}: {len(pool)} < {budget_per_class}")
        selected.extend(int(index) for index in rng.choice(pool, size=budget_per_class, replace=False))
    return sorted(selected)


def _validate_indices(indices: Iterable[int], rows: list[dict[str, str]], *, budget_per_class: int) -> list[int]:
    values = [int(index) for index in indices]
    if len(values) != 2 * budget_per_class or len(set(values)) != len(values):
        raise ValueError("split manifest has the wrong number of unique indices")
    if any(index < 0 or index >= len(rows) for index in values):
        raise ValueError("split manifest contains an out-of-range row index")
    counts = {label: sum(rows[index].get("label") == label for index in values) for label in LABELS}
    if counts != {label: budget_per_class for label in LABELS}:
        raise ValueError(f"split manifest is not stratified: {counts}")
    return sorted(values)


def validate_split_manifest(
    split_document: dict[str, Any],
    *,
    train_rows: list[dict[str, str]],
    dev_rows: list[dict[str, str]],
    train_member_sha256: str,
    dev_member_sha256: str,
) -> None:
    """Validate declared indices, source hashes, and class balance."""

    if split_document.get("train_member_sha256") != train_member_sha256:
        raise ValueError("split manifest train member hash does not match the verified archive member")
    if split_document.get("confirmation_member_sha256") != dev_member_sha256:
        raise ValueError("split manifest confirmation member hash does not match the verified archive member")
    budgets = [int(value) for value in split_document.get("budgets_per_class", [])]
    seeds = [int(value) for value in split_document.get("development_seeds", [])]
    selections = split_document.get("train_row_indices", {})
    for seed in seeds:
        for budget in budgets:
            declared = selections.get(str(seed), {}).get(str(budget))
            if declared is None:
                raise ValueError(f"missing train selection for seed={seed}, budget={budget}")
            expected = select_stratified_indices(train_rows, seed=seed, budget_per_class=budget)
            actual = _validate_indices(declared, train_rows, budget_per_class=budget)
            if actual != expected:
                raise ValueError(f"train selection is not reproducible for seed={seed}, budget={budget}")
    confirmation_budget = int(split_document["confirmation_budget_per_class"])
    confirmation_seeds = [int(value) for value in split_document.get("confirmation_seeds", [])]
    confirmation_selections = split_document.get("confirmation_row_indices", {})
    for seed in confirmation_seeds:
        declared = confirmation_selections.get(str(seed))
        if declared is None:
            raise ValueError(f"missing confirmation selection for seed={seed}")
        confirmation = _validate_indices(declared, dev_rows, budget_per_class=confirmation_budget)
        expected_confirmation = select_stratified_indices(
            dev_rows,
            seed=seed,
            budget_per_class=confirmation_budget,
        )
        if confirmation != expected_confirmation:
            raise ValueError(f"confirmation selection is not reproducible for seed={seed}")


def selected_examples(
    rows: list[dict[str, str]],
    *,
    source_member: str,
    row_indices: Iterable[int],
) -> list[dict[str, Any]]:
    """Return explicit, hash-addressable examples in manifest order."""

    examples = []
    for row_index in row_indices:
        index = int(row_index)
        row = rows[index]
        if "label" not in row:
            raise ValueError(f"selected row has no label: {source_member}[{index}]")
        examples.append(
            {
                "sample_id": sentence_sample_id(source_member, index, row["sentence"]),
                "source_member": source_member,
                "row_index": index,
                "sentence": row["sentence"],
                "label": int(row["label"]),
            }
        )
    return examples


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


__all__ = [
    "load_json",
    "read_tsv_member",
    "selected_examples",
    "select_stratified_indices",
    "sentence_sample_id",
    "validate_split_manifest",
]
