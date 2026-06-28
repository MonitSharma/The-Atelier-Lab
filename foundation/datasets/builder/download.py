import os
import json
import hashlib
from datasets import load_dataset
from tqdm import tqdm

def get_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def download_corpora(output_dir, limit=None, max_bytes=55_000_000):
    os.makedirs(output_dir, exist_ok=True)
    
    datasets_to_download = [
        {
            "name": "Henil1/sanskrit",
            "split": "train",
            "text_col": "text",
            "url": "https://huggingface.co/datasets/Henil1/sanskrit",
            "license": "MIT",
            "out_file": "raw_henil.jsonl"
        },
        {
            "name": "saucam/sans_data",
            "split": "train",
            "text_col": "text",
            "url": "https://huggingface.co/datasets/saucam/sans_data",
            "license": "CC-BY-SA-4.0",
            "out_file": "raw_sansdata.jsonl"
        }
    ]
    
    total_bytes_written = 0
    
    for cfg in datasets_to_download:
        if total_bytes_written >= max_bytes:
            print(f"Reached max bytes limit of {max_bytes:,}. Skipping remaining datasets.")
            break
            
        print(f"Downloading {cfg['name']}...")
        out_path = os.path.join(output_dir, cfg["out_file"])
        
        # Load in streaming mode to keep memory usage low
        ds = load_dataset(cfg["name"], split=cfg["split"], streaming=True)
        
        count = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for item in tqdm(ds, desc=f"Writing {cfg['out_file']}"):
                text = item.get(cfg["text_col"], "")
                if not text or not text.strip():
                    continue
                
                text_bytes = len(text.encode("utf-8"))
                
                doc = {
                    "id": get_hash(text),
                    "text": text,
                    "source": cfg["name"],
                    "download_url": cfg["url"],
                    "license": cfg["license"],
                    "title": item.get("title", "Unknown"),
                    "author": item.get("author", "Unknown"),
                    "pipeline_steps": ["downloaded"]
                }
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                count += 1
                total_bytes_written += text_bytes
                
                if total_bytes_written >= max_bytes:
                    print(f"Reached max bytes limit of {max_bytes:,} during download of {cfg['name']}.")
                    break
                if limit and count >= limit:
                    break
        print(f"Finished downloading {cfg['name']}: {count} records written to {out_path}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download raw corpora.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save raw jsonl files.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of documents downloaded per dataset.")
    parser.add_argument("--max_bytes", type=int, default=55000000, help="Max raw text bytes to download across all corpora.")
    args = parser.parse_args()
    
    download_corpora(args.output_dir, args.limit, args.max_bytes)
