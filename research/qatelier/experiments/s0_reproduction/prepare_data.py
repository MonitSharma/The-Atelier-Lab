"""Prepare immutable, pinned S0 embeddings and train-only compressors."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from research.qatelier.data.representations import (
    CompressorArtifact,
    FrozenRepresentationManifest,
    stable_array_hash,
)
from research.qatelier.experiments.s0_reproduction.splits import (
    load_json,
    read_tsv_member,
    selected_examples,
    validate_split_manifest,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_archive(archive: Path, expected_sha256: str) -> None:
    actual = _sha256_file(archive)
    if actual != expected_sha256:
        raise ValueError(f"SST-2 archive hash mismatch: {actual} != {expected_sha256}")


def _verify_encoder_weights(encoder_path: Path, expected_sha256: str) -> Path:
    candidates = sorted(encoder_path.rglob("model.safetensors"))
    if not candidates:
        raise FileNotFoundError(f"no model.safetensors found under encoder path: {encoder_path}")
    matches = [candidate for candidate in candidates if _sha256_file(candidate) == expected_sha256]
    if len(matches) != 1:
        found = ", ".join(str(candidate) for candidate in candidates)
        raise ValueError(f"encoder weights digest did not identify exactly one file; candidates: {found}")
    return matches[0]


def _load_sentence_encoder(encoder_path: Path):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - exercised only without the optional stack
        raise RuntimeError("S0 preparation requires the optional sentence-transformers stack") from exc
    model = SentenceTransformer(str(encoder_path), local_files_only=True)
    model.eval()
    return model


def _encode(model: Any, sentences: list[str], expected_dimension: int) -> np.ndarray:
    embeddings = model.encode(
        sentences,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=False,
        show_progress_bar=False,
    )
    values = np.asarray(embeddings, dtype=np.float32)
    if values.shape != (len(sentences), expected_dimension):
        raise ValueError(f"encoder returned {values.shape}, expected {(len(sentences), expected_dimension)}")
    if not np.all(np.isfinite(values)):
        raise ValueError("encoder returned non-finite embeddings")
    return values


def prepare_s0(
    *,
    config_path: str | Path,
    archive_path: str | Path,
    encoder_path: str | Path,
    output_dir: str | Path,
) -> Path:
    """Validate all locks, encode the declared union, and fit train-only PCA files."""

    config = yaml.safe_load(Path(config_path).read_text())
    s0_dir = Path(config_path).parent
    data_manifest_path = s0_dir / config["dataset"]["split_manifest"]
    encoder_manifest_path = s0_dir / config["artifacts"]["embedding_manifest"]
    data_manifest = load_json(data_manifest_path)
    encoder_manifest = load_json(encoder_manifest_path)
    archive = Path(archive_path)
    encoder_root = Path(encoder_path)
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"S0 output directory must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    if config["encoder"]["revision"] != encoder_manifest["encoder_revision"]:
        raise ValueError("config and encoder manifest revisions differ")
    if config["encoder"]["weights_digest"] != encoder_manifest["weights_sha256"]:
        raise ValueError("config and encoder manifest weights digests differ")
    _verify_archive(archive, data_manifest["archive_sha256"])
    protocol = data_manifest["protocol_split"]
    train_member = protocol["training_source"]
    dev_member = protocol["development_source"]
    weights_path = _verify_encoder_weights(encoder_root, encoder_manifest["weights_sha256"])
    train = read_tsv_member(
        archive,
        train_member,
        expected_sha256=data_manifest["members"][train_member]["sha256"],
    )
    dev = read_tsv_member(
        archive,
        dev_member,
        expected_sha256=data_manifest["members"][dev_member]["sha256"],
    )
    validate_split_manifest(
        load_json(s0_dir / "split_manifest.json"),
        train_rows=train,
        dev_rows=dev,
        train_member_sha256=data_manifest["members"][train_member]["sha256"],
        dev_member_sha256=data_manifest["members"][dev_member]["sha256"],
    )

    split_document = load_json(s0_dir / "split_manifest.json")
    requested: set[tuple[str, int]] = set()
    for selections in split_document["train_row_indices"].values():
        for indices in selections.values():
            requested.update((split_document["train_member"], int(index)) for index in indices)
    requested.update((split_document["confirmation_member"], int(index)) for index in split_document["confirmation_row_indices"])
    examples_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for example in selected_examples(
        train,
        source_member=split_document["train_member"],
        row_indices=sorted(index for member, index in requested if member == split_document["train_member"]),
    ):
        examples_by_key[(example["source_member"], example["row_index"])] = example
    for example in selected_examples(
        dev,
        source_member=split_document["confirmation_member"],
        row_indices=sorted(index for member, index in requested if member == split_document["confirmation_member"]),
    ):
        examples_by_key[(example["source_member"], example["row_index"])] = example
    examples = [examples_by_key[key] for key in sorted(examples_by_key)]
    model = _load_sentence_encoder(encoder_root)
    embeddings = _encode(model, [example["sentence"] for example in examples], encoder_manifest["embedding_dimension"])
    sample_ids = [example["sample_id"] for example in examples]
    sample_ids_hash = hashlib.sha256(json.dumps(sample_ids, separators=(",", ":")).encode()).hexdigest()
    representation_manifest = FrozenRepresentationManifest(
        encoder_model_id=encoder_manifest["encoder_model_id"],
        encoder_revision=encoder_manifest["encoder_revision"],
        weights_digest=encoder_manifest["weights_sha256"],
        embedding_dim=embeddings.shape[1],
        tokenizer_settings=encoder_manifest["tokenizer"],
        pooling=encoder_manifest["pooling"]["type"],
        normalization="none",
        sample_ids_hash=sample_ids_hash,
        embeddings_hash=stable_array_hash(embeddings),
    )
    np.savez_compressed(destination / "embeddings.npz", sample_ids=np.asarray(sample_ids), embeddings=embeddings)
    (destination / "embedding_manifest.json").write_text(json.dumps(representation_manifest.to_dict(), indent=2, sort_keys=True) + "\n")
    (destination / "examples.json").write_text(json.dumps(examples, indent=2, sort_keys=True) + "\n")

    compressor_dir = destination / "compressors"
    compressor_dir.mkdir()
    index_lookup = {example["sample_id"]: index for index, example in enumerate(examples)}
    compressor_records = []
    for seed, selections in split_document["train_row_indices"].items():
        for budget, indices in selections.items():
            ids = [
                examples_by_key[(split_document["train_member"], int(row_index))]["sample_id"]
                for row_index in indices
            ]
            features = embeddings[[index_lookup[sample_id] for sample_id in ids]]
            artifact = CompressorArtifact.fit(
                features,
                train_sample_ids=ids,
                output_dim=int(config["representation"]["compressor"]["output_dim"]),
                fit_split="train",
            )
            path = artifact.save(compressor_dir / f"seed-{seed}-budget-{budget}.npz")
            compressor_records.append({"seed": int(seed), "budget_per_class": int(budget), **artifact.to_metadata(), "path": str(path.relative_to(destination))})
    preparation_manifest = {
        "schema_version": 1,
        "config_sha256": _manifest_file_hash(Path(config_path)),
        "data_manifest_sha256": _manifest_file_hash(data_manifest_path),
        "encoder_manifest_sha256": _manifest_file_hash(encoder_manifest_path),
        "archive_sha256": data_manifest["archive_sha256"],
        "encoder_weights_path": str(weights_path),
        "encoder_weights_sha256": encoder_manifest["weights_sha256"],
        "sample_count": len(examples),
        "embedding_dimension": int(embeddings.shape[1]),
        "embeddings_hash": stable_array_hash(embeddings),
        "compressors": compressor_records,
    }
    (destination / "preparation_manifest.json").write_text(json.dumps(preparation_manifest, indent=2, sort_keys=True) + "\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--encoder-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = prepare_s0(
        config_path=args.config,
        archive_path=args.archive,
        encoder_path=args.encoder_path,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": "prepared", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
