"""Prepare the pinned CoLA frozen-sentence representation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from research.qatelier.data.representations import CompressorArtifact, stable_array_hash


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path, expected_hash: str, expected_rows: int) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("CoLA preparation requires pyarrow") from exc
    if _sha256(path) != expected_hash:
        raise ValueError(f"CoLA parquet hash mismatch: {path}")
    table = parquet.read_table(path)
    if table.num_rows != expected_rows:
        raise ValueError(f"CoLA row count mismatch: {table.num_rows} != {expected_rows}")
    columns = table.to_pydict()
    return [dict(zip(columns, values)) for values in zip(*columns.values())]


def prepare_cola(*, config_path: str | Path, train_path: str | Path, validation_path: str | Path, encoder_path: str | Path, output_dir: str | Path) -> Path:
    config_path = Path(config_path)
    config = yaml.safe_load(config_path.read_text())
    root = config_path.parent
    data_manifest = json.loads((root / config["additional_classification"]["data_manifest"]).read_text())
    split_manifest = json.loads((root / config["additional_classification"]["split_manifest"]).read_text())
    encoder_manifest = json.loads((root / config["additional_classification"]["encoder_manifest"]).read_text())
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"CoLA output directory must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    train = _read(Path(train_path), data_manifest["members"]["train"]["sha256"], data_manifest["members"]["train"]["rows"])
    validation = _read(Path(validation_path), data_manifest["members"]["validation"]["sha256"], data_manifest["members"]["validation"]["rows"])
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("CoLA preparation requires sentence-transformers") from exc
    weights = sorted(Path(encoder_path).rglob("model.safetensors"))
    if len([path for path in weights if _sha256(path) == encoder_manifest["weights_sha256"]]) != 1:
        raise ValueError("CoLA encoder path does not contain exactly one matching pinned weights file")
    model = SentenceTransformer(str(encoder_path), local_files_only=True)
    model.eval()
    requested: set[tuple[str, int]] = set()
    for selections in split_manifest["train_row_indices"].values():
        for indices in selections.values():
            requested.update(("train", int(index)) for index in indices)
    for indices in split_manifest["confirmation_row_indices"].values():
        requested.update(("validation", int(index)) for index in indices)
    rows_by_key = {("train", index): row for index, row in enumerate(train)} | {("validation", index): row for index, row in enumerate(validation)}
    examples = [{"sample_id": f"cola-{member}-{index}-idx-{int(rows_by_key[(member, index)]['idx'])}", "member": member, "row_index": index, "sentence": rows_by_key[(member, index)]["sentence"], "label": int(rows_by_key[(member, index)]["label"])} for member, index in sorted(requested)]
    sentences = [example["sentence"] for example in examples]
    embeddings = np.asarray(model.encode(sentences, batch_size=32, convert_to_numpy=True, normalize_embeddings=False, show_progress_bar=False), dtype=np.float32)
    sample_ids = [example["sample_id"] for example in examples]
    np.savez_compressed(destination / "embeddings.npz", sample_ids=np.asarray(sample_ids), embeddings=embeddings, labels=np.asarray([example["label"] for example in examples]))
    (destination / "examples.json").write_text(json.dumps(examples, indent=2, sort_keys=True) + "\n")
    lookup = {sample_id: index for index, sample_id in enumerate(sample_ids)}
    compressor_dir = destination / "compressors"
    compressor_dir.mkdir()
    compressors = []
    for seed, selections in split_manifest["train_row_indices"].items():
        for budget, indices in selections.items():
            ids = [f"cola-train-{int(index)}-idx-{int(train[int(index)]['idx'])}" for index in indices]
            artifact = CompressorArtifact.fit(embeddings[[lookup[sample_id] for sample_id in ids]], train_sample_ids=ids, output_dim=int(config["additional_classification"]["compressor_output_dim"]), fit_split="train")
            path = artifact.save(compressor_dir / f"seed-{seed}-budget-{budget}.npz")
            compressors.append({"seed": int(seed), "budget_per_class": int(budget), "path": str(path.relative_to(destination)), **artifact.to_metadata()})
    preparation = {"schema_version": 1, "task": "CoLA", "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(), "data_manifest_sha256": hashlib.sha256((root / config["additional_classification"]["data_manifest"]).read_bytes()).hexdigest(), "split_manifest_sha256": hashlib.sha256((root / config["additional_classification"]["split_manifest"]).read_bytes()).hexdigest(), "encoder_revision": encoder_manifest["encoder_revision"], "encoder_weights_sha256": encoder_manifest["weights_sha256"], "sample_count": len(examples), "embedding_dimension": int(embeddings.shape[1]), "embeddings_hash": stable_array_hash(embeddings), "compressors": compressors}
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
    destination = prepare_cola(config_path=args.config, train_path=args.train, validation_path=args.validation, encoder_path=args.encoder_path, output_dir=args.output_dir)
    print(json.dumps({"status": "prepared", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
