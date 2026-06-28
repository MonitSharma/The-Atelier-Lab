import os
import json
import re
import unicodedata
from tqdm import tqdm

def calculate_quality_score(text, config):
    filters = config.get("filters", {})
    min_chars = filters.get("min_chars", 100)
    max_digit_ratio = filters.get("max_digit_ratio", 0.10)
    max_punctuation_ratio = filters.get("max_punctuation_ratio", 0.15)
    
    total_len = len(text)
    if total_len == 0:
        return 0, {"reason": "Empty document"}
        
    score_unicode = 20
    # Check if text is NFC normalized
    if unicodedata.normalize("NFC", text) != text:
        score_unicode = 10
        
    # Devanagari ratio score (out of 30)
    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
    alphabetic_chars = len(re.findall(r"[a-zA-Z\u0900-\u097F]", text))
    if alphabetic_chars > 0:
        devanagari_ratio = devanagari_chars / alphabetic_chars
    else:
        devanagari_ratio = 0.0
    score_script = 30 * devanagari_ratio
    
    # Digit and Punctuation clean score (out of 30)
    digit_chars = len(re.findall(r"\d", text))
    digit_ratio = digit_chars / total_len
    
    # Non-alphanumeric, non-whitespace
    punct_chars = len(re.findall(r"[^\w\s\u0900-\u097F]", text))
    punct_ratio = punct_chars / total_len
    
    # Score drops if digit or punctuation ratios exceed limits
    score_clean = 30
    if digit_ratio > max_digit_ratio:
        penalty = (digit_ratio - max_digit_ratio) / (1.0 - max_digit_ratio) * 15
        score_clean -= min(15, penalty * 15)
    if punct_ratio > max_punctuation_ratio:
        penalty = (punct_ratio - max_punctuation_ratio) / (1.0 - max_punctuation_ratio) * 15
        score_clean -= min(15, penalty * 15)
        
    # Document length score (out of 20)
    score_length = 20
    if total_len < min_chars:
        score_length = 20 * (total_len / min_chars)
        
    final_score = int(score_unicode + score_script + score_clean + score_length)
    
    breakdown = {
        "score_unicode": score_unicode,
        "score_script": int(score_script),
        "score_clean": int(score_clean),
        "score_length": int(score_length),
        "devanagari_ratio": devanagari_ratio,
        "digit_ratio": digit_ratio,
        "punct_ratio": punct_ratio,
        "total_chars": total_len
    }
    
    return final_score, breakdown

def filter_directory(input_dir, output_dir, config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    filters = config.get("filters", {})
    quality_threshold = filters.get("quality_threshold", 80)
    
    os.makedirs(output_dir, exist_ok=True)
    
    metadata_dir = os.path.join(os.path.dirname(output_dir), "metadata")
    os.makedirs(metadata_dir, exist_ok=True)
    
    discarded_path = os.path.join(metadata_dir, "discarded_logs.jsonl")
    
    stats = {
        "scanned": 0,
        "accepted": 0,
        "rejected": 0
    }
    
    with open(discarded_path, "w", encoding="utf-8") as fdiscard:
        for filename in os.listdir(input_dir):
            if not filename.endswith(".jsonl"):
                continue
                
            in_path = os.path.join(input_dir, filename)
            out_path = os.path.join(output_dir, f"final_{filename.replace('deduplicated_', '')}")
            
            print(f"Filtering {filename}...")
            
            with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
                for line_json in tqdm(fin, desc="Filtering documents"):
                    stats["scanned"] += 1
                    doc = json.loads(line_json)
                    text = doc["text"].strip()
                    
                    score, breakdown = calculate_quality_score(text, config)
                    
                    # Store score and audit history
                    doc["quality_score"] = score
                    doc["quality_breakdown"] = breakdown
                    
                    if score >= quality_threshold:
                        doc["pipeline_steps"].append("quality_filtered")
                        fout.write(json.dumps(doc, ensure_ascii=False) + "\n")
                        stats["accepted"] += 1
                    else:
                        doc["rejection_reason"] = breakdown
                        fdiscard.write(json.dumps(doc, ensure_ascii=False) + "\n")
                        stats["rejected"] += 1
                        
            print(f"Filtered {filename}: {stats['accepted']} accepted, {stats['rejected']} rejected.")
            
    print("\n=== Filtering Quality Statistics ===")
    print(f"Scanned documents: {stats['scanned']:,}")
    print(f"Accepted (score >= {quality_threshold}): {stats['accepted']:,}")
    print(f"Rejected (score < {quality_threshold}): {stats['rejected']:,}")
    
    # Save filter stats helper metrics
    with open(os.path.join(metadata_dir, "filter_stats.json"), "w") as f:
        json.dump(stats, f)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Calculate quality score and filter documents.")
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    
    filter_directory(args.input_dir, args.output_dir, args.config)
