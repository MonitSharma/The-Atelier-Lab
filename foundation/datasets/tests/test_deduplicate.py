import os
import json
import tempfile
import pytest
from foundation.datasets.builder.deduplicate import deduplicate_directory

def test_deduplicate_run():
    # Setup temp dirs
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        # Write config
        config = {
            "filters": {
                "remove_duplicate_lines": True,
                "remove_duplicate_paragraphs": True
            }
        }
        config_path = os.path.join(tmp_in, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)
            
        # Write duplicate records jsonl
        doc1 = {"id": "1", "text": "क ख ग\n\nक ख ग", "pipeline_steps": []} # Paragraph duplicate
        doc2 = {"id": "2", "text": "क ख ग", "pipeline_steps": []} # Exact doc duplicate
        doc3 = {"id": "3", "text": "क ख ग\nक ख ग", "pipeline_steps": []} # Line duplicate (local)
        
        in_file = os.path.join(tmp_in, "cleaned_test.jsonl")
        with open(in_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(doc1) + "\n")
            f.write(json.dumps(doc2) + "\n")
            f.write(json.dumps(doc3) + "\n")
            
        # Run dedup
        deduplicate_directory(tmp_in, tmp_out, config_path)
        
        # Verify outputs
        out_file = os.path.join(tmp_out, "deduplicated_test.jsonl")
        assert os.path.exists(out_file)
        
        results = []
        with open(out_file, "r", encoding="utf-8") as f:
            for line in f:
                results.append(json.loads(line))
                
        # Doc 2 is removed (exact duplicate of doc 1 paragraph-deduped text "क ख ग")
        assert len(results) == 2
        # Doc 1 (paragraph-deduped) text is "क ख ग"
        assert results[0]["text"] == "क ख ग"
        # Doc 3 (line-deduped) text is "क ख ग"
        assert results[1]["text"] == "क ख ग"
