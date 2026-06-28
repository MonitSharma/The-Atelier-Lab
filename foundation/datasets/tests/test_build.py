import os
import json
import tempfile
import pyarrow.parquet as pq
import pytest
from foundation.datasets.builder.build_dataset import compile_dataset

def test_parquet_compilation():
    with tempfile.TemporaryDirectory() as tmp_clean, tempfile.TemporaryDirectory() as tmp_out, tempfile.TemporaryDirectory() as tmp_meta:
        # Create final jsonl data
        doc1 = {
            "id": "abc",
            "text": "क ख ग",
            "source": "Henil1/sanskrit",
            "download_url": "...",
            "license": "MIT",
            "title": "Test Title",
            "author": "Test Author",
            "quality_score": 90,
            "pipeline_steps": []
        }
        
        doc_file = os.path.join(tmp_clean, "final_test.jsonl")
        with open(doc_file, "w", encoding="utf-8") as f:
            for _ in range(20):
                f.write(json.dumps(doc1) + "\n")
            
        # Write dummy manifest_data.json
        manifest_data = {
            "version": "SanskritPile-v1",
            "total_documents": 20,
            "total_characters": 100,
            "total_bytes": 300,
            "duplicate_rate": 0.0,
            "sources": {"Henil1/sanskrit": 300}
        }
        with open(os.path.join(tmp_meta, "manifest_data.json"), "w") as f:
            json.dump(manifest_data, f)
            
        # Run compile
        compile_dataset(tmp_clean, tmp_out, tmp_meta)
        
        # Verify Parquet files
        train_shard = os.path.join(tmp_out, "shard_00000.parquet")
        assert os.path.exists(train_shard)
        
        table = pq.read_table(train_shard)
        assert table.num_rows == 19
        assert table.column("text")[0].as_py() == "क ख ग"
        assert table.column("quality_score")[0].as_py() == 90
        
        # Verify manifest.json
        manifest_path = os.path.join(tmp_out, "manifest.json")
        assert os.path.exists(manifest_path)
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        assert manifest["version"] == "SanskritPile-v1"
        assert manifest["total_documents"] == 20
