"""Download-free preparation of the pinned SciFact embeddings and compressors."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from research.qatelier.data.representations import CompressorArtifact, stable_array_hash


ROOT = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _text(title: Any, body: Any) -> str:
    title = str(title or "").strip()
    body = str(body or "").strip()
    return f"{title}\n{body}" if title else body


def _qrels(path: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    with path.open(newline="") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            if int(row["score"]) == 1:
                result.setdefault(str(row["query-id"]), []).append(str(row["corpus-id"]))
    return result


def prepare(*, config_path: str | Path, data_dir: str | Path, encoder_path: str | Path, output_dir: str | Path) -> Path:
    config_path = Path(config_path)
    data_dir = Path(data_dir)
    encoder_path = Path(encoder_path)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"retrieval preparation output must be new and empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads(json.dumps(__import__("yaml").safe_load(config_path.read_text())))
    data_manifest = json.loads((config_path.parent / config["sources"]["data_manifest"]).read_text())
    split_manifest = json.loads((config_path.parent / config["sources"]["split_manifest"]).read_text())
    members = data_manifest["members"]
    for member in members.values():
        path = data_dir / member["path"]
        if _sha256(path) != member["sha256"]:
            raise ValueError(f"source hash mismatch for {member['path']}")
    try:
        import pyarrow.parquet as parquet
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - optional data environment
        raise RuntimeError("retrieval preparation requires pyarrow and sentence-transformers") from exc

    corpus_table = parquet.read_table(data_dir / members["corpus"]["path"]).to_pylist()
    query_table = parquet.read_table(data_dir / members["queries"]["path"]).to_pylist()
    corpus_ids = [str(row["_id"]) for row in corpus_table]
    query_ids = [str(row["_id"]) for row in query_table]
    corpus_text = [_text(row["title"], row["text"]) for row in corpus_table]
    query_text = [_text(row["title"], row["text"]) for row in query_table]
    model = SentenceTransformer(str(encoder_path), local_files_only=True)
    weights = sorted(encoder_path.rglob("model.safetensors"))
    if len(weights) != 1 or _sha256(weights[0]) != config["representation"]["encoder_weights_sha256"]:
        raise ValueError("encoder weights do not match the pinned MPNet digest")
    corpus_embeddings = np.asarray(model.encode(corpus_text, batch_size=32, convert_to_numpy=True, normalize_embeddings=False, show_progress_bar=True), dtype=np.float32)
    query_embeddings = np.asarray(model.encode(query_text, batch_size=32, convert_to_numpy=True, normalize_embeddings=False, show_progress_bar=True), dtype=np.float32)
    if corpus_embeddings.shape[1] != 768 or query_embeddings.shape[1] != 768:
        raise ValueError("unexpected MPNet embedding dimension")
    np.savez_compressed(output_dir / "embeddings.npz", corpus_ids=np.asarray(corpus_ids), query_ids=np.asarray(query_ids), corpus_embeddings=corpus_embeddings, query_embeddings=query_embeddings)
    train_qrels = _qrels(data_dir / members["qrels_train"]["path"])
    (output_dir / "qrels_train.json").write_text(json.dumps(train_qrels, indent=2, sort_keys=True) + "\n")
    (output_dir / "qrels_test.json").write_text(json.dumps(_qrels(data_dir / members["qrels_test"]["path"]), indent=2, sort_keys=True) + "\n")
    corpus_index = {doc_id: index for index, doc_id in enumerate(corpus_ids)}
    query_index = {query_id: index for index, query_id in enumerate(query_ids)}
    representations: list[dict[str, Any]] = []
    representation_dir = output_dir / "representations"
    for train_seed, selections in split_manifest["training_query_ids"].items():
        for budget_text, selected_queries in selections.items():
            selected_docs = sorted({doc_id for query_id in selected_queries for doc_id in train_qrels[str(query_id)]})
            fit_indices = [corpus_index[doc_id] for doc_id in selected_docs]
            compressor = CompressorArtifact.fit(corpus_embeddings[fit_indices], train_sample_ids=selected_docs, output_dim=int(config["representation"]["compressor_output_dim"]))
            compressor_path = representation_dir / f"compressor-seed-{train_seed}-budget-{budget_text}.npz"
            compressor.save(compressor_path)
            corpus_features = compressor.transform(corpus_embeddings).astype(np.float32)
            query_features = compressor.transform(query_embeddings).astype(np.float32)
            feature_path = representation_dir / f"features-seed-{train_seed}-budget-{budget_text}.npz"
            np.savez_compressed(feature_path, corpus_ids=np.asarray(corpus_ids), query_ids=np.asarray(query_ids), corpus_features=corpus_features, query_features=query_features)
            representations.append({"train_seed": int(train_seed), "budget": int(budget_text), "selected_query_count": len(selected_queries), "fit_document_count": len(selected_docs), "compressor": str(compressor_path.relative_to(output_dir)), "features": str(feature_path.relative_to(output_dir)), "compressor_metadata": compressor.to_metadata(), "corpus_features_hash": stable_array_hash(corpus_features), "query_features_hash": stable_array_hash(query_features), "selected_query_indices": [query_index[str(query_id)] for query_id in selected_queries]})
    manifest = {"schema_version": 1, "experiment_id": config["experiment_id"], "status": "prepared_train_only_compressed_embeddings", "config_sha256": _sha256(config_path), "data_manifest_sha256": _sha256(config_path.parent / config["sources"]["data_manifest"]), "split_manifest_sha256": _sha256(config_path.parent / config["sources"]["split_manifest"]), "encoder_weights_sha256": _sha256(weights[0]), "corpus_count": len(corpus_ids), "query_count": len(query_ids), "embedding_dimension": int(corpus_embeddings.shape[1]), "corpus_embeddings_hash": stable_array_hash(corpus_embeddings), "query_embeddings_hash": stable_array_hash(query_embeddings), "representations": representations, "provider_contacted": False, "jobs_submitted": 0}
    (output_dir / "preparation_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--encoder-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = prepare(config_path=args.config, data_dir=args.data_dir, encoder_path=args.encoder_path, output_dir=args.output_dir)
    print(json.dumps({"status": "prepared", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
