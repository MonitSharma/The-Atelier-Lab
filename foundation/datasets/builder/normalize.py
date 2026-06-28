import os
import json
import unicodedata
import re
from tqdm import tqdm

def normalize_text(text):
    # Normalize Unicode to NFC
    text = unicodedata.normalize("NFC", text)
    
    # Normalize whitespaces: collapse spaces/tabs on each line
    lines = []
    for line in text.split("\n"):
        line_clean = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line_clean)
        
    # Collapse multiple consecutive blank lines to at most one empty line
    collapsed_lines = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty:
                collapsed_lines.append("")
                prev_empty = True
        else:
            collapsed_lines.append(line)
            prev_empty = False
            
    return "\n".join(collapsed_lines).strip()

def normalize_directory(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    for filename in os.listdir(input_dir):
        if not filename.endswith(".jsonl"):
            continue
            
        in_path = os.path.join(input_dir, filename)
        out_path = os.path.join(output_dir, f"normalized_{filename}")
        
        print(f"Normalizing {filename}...")
        count = 0
        with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
            for line in tqdm(fin, desc="Normalizing documents"):
                doc = json.loads(line)
                doc["text"] = normalize_text(doc["text"])
                doc["pipeline_steps"].append("unicode_normalized")
                fout.write(json.dumps(doc, ensure_ascii=False) + "\n")
                count += 1
                
        print(f"Normalized {count} docs from {filename} to {out_path}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Normalize Unicode and whitespace.")
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    args = parser.parse_args()
    
    normalize_directory(args.input_dir, args.output_dir)
