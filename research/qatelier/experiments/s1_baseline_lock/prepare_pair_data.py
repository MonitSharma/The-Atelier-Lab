"""Prepare the frozen MRPC pair representation for the S1 task."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from research.qatelier.data.representations import CompressorArtifact, make_pair_representation, stable_array_hash


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_member(path: Path, expected_sha256: str, expected_rows: int) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:  # pragma: no cover - optional environment
        raise RuntimeError("MRPC preparation requires pyarrow") from exc
    if _sha256(path) != expected_sha256:
        raise ValueError(f"MRPC parquet hash mismatch: {path}")
    table = parquet.read_table(path)
    if table.num_rows != expected_rows:
        raise ValueError(f"MRPC row count mismatch for {path}: {table.num_rows} != {expected_rows}")
    columns = table.to_pydict()
    return [dict(zip(columns, values)) for values in zip(*columns.values())]


def _pair_id(member: str, row_index: int, row: dict[str, Any]) -> str:
    return f"mrpc-{member}-{row_index}-idx-{int(row['idx'])}"


def _load_encoder(path: Path, expected_sha256: str):
    weights = sorted(path.rglob("model.safetensors"))
    matches = [candidate for candidate in weights if _sha256(candidate) == expected_sha256]
    if len(matches) != 1:
        raise ValueError("MRPC encoder path does not contain exactly one matching pinned weights file")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - optional environment
        raise RuntimeError("MRPC preparation requires sentence-transformers") from exc
    model = SentenceTransformer(str(path), local_files_only=True)
    model.eval()
    return model, matches[0]


def prepare_mrpc(*, config_path: str | Path, train_path: str | Path, validation_path: str | Path, encoder_path: str | Path, output_dir: str | Path) -> Path:
    config_path = Path(config_path)
    config = yaml.safe_load(config_path.read_text())
    root = config_path.parent
    data_manifest = json.loads((root / config["pair_task"]["data_manifest"]).read_text())
    split_manifest = json.loads((root / config["pair_task"]["split_manifest"]).read_text())
    encoder_manifest = json.loads((root / config["pair_task"]["encoder_manifest"]).read_text())
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"MRPC output directory must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    train_rows = _read_member(Path(train_path), data_manifest["members"]["train"]["sha256"], data_manifest["members"]["train"]["rows"])
    validation_rows = _read_member(Path(validation_path), data_manifest["members"]["validation"]["sha256"], data_manifest["members"]["validation"]["rows"])
    model, weights_path = _load_encoder(Path(encoder_path), encoder_manifest["weights_sha256"])
    requested: set[tuple[str, int]] = set()
    for selections in split_manifest["train_row_indices"].values():
        for indices in selections.values():
            requested.update(("train", int(index)) for index in indices)
    for indices in split_manifest["confirmation_row_indices"].values():
        requested.update(("validation", int(index)) for index in indices)
    rows_by_key = {("train", index): row for index, row in enumerate(train_rows)} | {("validation", index): row for index, row in enumerate(validation_rows)}
    examples = []
    for member, index in sorted(requested):
        row = rows_by_key[(member, index)]
        examples.append({"sample_id": _pair_id(member, index, row), "member": member, "row_index": index, "idx": int(row["idx"]), "sentence1": row["sentence1"], "sentence2": row["sentence2"], "label": int(row["label"])})
    unique_sentences = sorted({text for example in examples for text in (example["sentence1"], example["sentence2"])})
    encoded = model.encode(unique_sentences, batch_size=32, convert_to_numpy=True, normalize_embeddings=False, show_progress_bar=False)
    sentence_embeddings = {sentence: np.asarray(vector, dtype=np.float32) for sentence, vector in zip(unique_sentences, encoded)}
    pair_features = make_pair_representation(
        np.asarray([sentence_embeddings[example["sentence1"]] for example in examples]),
        np.asarray([sentence_embeddings[example["sentence2"]] for example in examples]),
    ).astype(np.float32)
    sample_ids = [example["sample_id"] for example in examples]
    np.savez_compressed(destination / "pair_embeddings.npz", sample_ids=np.asarray(sample_ids), features=pair_features, labels=np.asarray([example["label"] for example in examples]))
    (destination / "pair_examples.json").write_text(json.dumps(examples, indent=2, sort_keys=True) + "\n")
    lookup = {sample_id: index for index, sample_id in enumerate(sample_ids)}
    compressors = []
    compressor_dir = destination / "compressors"
    compressor_dir.mkdir()
    for seed, selections in split_manifest["train_row_indices"].items():
        for budget, indices in selections.items():
            ids = [_pair_id("train", int(index), train_rows[int(index)]) for index in indices]
            artifact = CompressorArtifact.fit(pair_features[[lookup[sample_id] for sample_id in ids]], train_sample_ids=ids, output_dim=int(config["pair_task"]["compressor_output_dim"]), fit_split="train")
            path = artifact.save(compressor_dir / f"seed-{seed}-budget-{budget}.npz")
            compressors.append({"seed": int(seed), "budget_per_class": int(budget), "path": str(path.relative_to(destination)), **artifact.to_metadata()})
    preparation = {
        "schema_version": 1,
        "task": "MRPC",
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "data_manifest_sha256": hashlib.sha256((root / config["pair_task"]["data_manifest"]).read_bytes()).hexdigest(),
        "split_manifest_sha256": hashlib.sha256((root / config["pair_task"]["split_manifest"]).read_bytes()).hexdigest(),
        "encoder_revision": encoder_manifest["encoder_revision"],
        "encoder_weights_sha256": encoder_manifest["weights_sha256"],
        "encoder_weights_path": str(weights_path),
        "sample_count": len(examples),
        "pair_feature_dimension": int(pair_features.shape[1]),
        "pair_features_hash": stable_array_hash(pair_features),
        "compressors": compressors,
    }
    (destination / "preparation_manifest.json").write_text(json.dumps(preparation, indent=2, sort_keys=True) + "\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--encoder-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = prepare_mrpc(config_path=args.config, train_path=args.train, validation_path=args.validation, encoder_path=args.encoder_path, output_dir=args.output_dir)
    print(json.dumps({"status": "prepared", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
