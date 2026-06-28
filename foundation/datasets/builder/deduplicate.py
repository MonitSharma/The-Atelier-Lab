import os
import json
import hashlib
from tqdm import tqdm

def get_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def deduplicate_directory(input_dir, output_dir, config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    filters = config.get("filters", {})
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Global sets for deduplication
    seen_doc_hashes = set()
    seen_para_hashes = set()
    
    # Statistics
    stats = {
        "original_docs": 0,
        "docs_removed_exact": 0,
        "paragraphs_removed_global": 0,
        "lines_removed_local": 0,
        "final_docs": 0
    }
    
    for filename in os.listdir(input_dir):
        if not filename.endswith(".jsonl"):
            continue
            
        in_path = os.path.join(input_dir, filename)
        out_path = os.path.join(output_dir, f"deduplicated_{filename.replace('cleaned_', '')}")
        
        print(f"Deduplicating {filename}...")
        
        docs_written = 0
        with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
            for line_json in tqdm(fin, desc="Deduplicating documents"):
                stats["original_docs"] += 1
                doc = json.loads(line_json)
                text = doc["text"].strip()
                if not text:
                    continue
                    
                # 1. Document-level Deduplication (Exact Match)
                doc_hash = get_hash(text)
                if doc_hash in seen_doc_hashes:
                    stats["docs_removed_exact"] += 1
                    continue
                seen_doc_hashes.add(doc_hash)
                
                # 2. Paragraph-level Deduplication (Global)
                paragraphs = text.split("\n\n")
                unique_paragraphs = []
                for p in paragraphs:
                    p_strip = p.strip()
                    if not p_strip:
                        continue
                    p_hash = get_hash(p_strip)
                    if filters.get("remove_duplicate_paragraphs", True):
                        if p_hash in seen_para_hashes:
                            stats["paragraphs_removed_global"] += 1
                            continue
                        seen_para_hashes.add(p_hash)
                    unique_paragraphs.append(p_strip)
                
                text_para_dedup = "\n\n".join(unique_paragraphs)
                
                # 3. Line-level Deduplication (Local to document)
                lines = text_para_dedup.split("\n")
                unique_lines = []
                seen_line_hashes_local = set()
                
                for line in lines:
                    line_strip = line.strip()
                    if not line_strip:
                        continue
                    line_hash = get_hash(line_strip)
                    if filters.get("remove_duplicate_lines", True):
                        if line_hash in seen_line_hashes_local:
                            stats["lines_removed_local"] += 1
                            continue
                        seen_line_hashes_local.add(line_hash)
                    unique_lines.append(line_strip)
                    
                final_text = "\n".join(unique_lines).strip()
                
                if final_text:
                    doc["text"] = final_text
                    doc["pipeline_steps"].append("deduplicated")
                    fout.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    docs_written += 1
                    
        stats["final_docs"] += docs_written
        print(f"Deduplicated {filename}: {docs_written} docs written to {out_path}.")
        
    print("\n=== Deduplication Statistics ===")
    print(f"Original documents scanned: {stats['original_docs']:,}")
    print(f"Exact duplicates removed: {stats['docs_removed_exact']:,}")
    print(f"Boilerplate paragraphs removed globally: {stats['paragraphs_removed_global']:,}")
    print(f"Cyclic duplicate lines removed locally: {stats['lines_removed_local']:,}")
    print(f"Final documents preserved: {stats['final_docs']:,}")
    
    # Save statistics report helper metrics
    project_dir = os.path.dirname(os.path.dirname(output_dir))
    metadata_dir = os.path.join(project_dir, "metadata")
    os.makedirs(metadata_dir, exist_ok=True)
    with open(os.path.join(metadata_dir, "dedup_stats.json"), "w") as f:
        json.dump(stats, f)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multi-level deduplication of documents, paragraphs, and lines.")
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    
    deduplicate_directory(args.input_dir, args.output_dir, args.config)
