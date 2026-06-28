import os
import json
import math
import re
from collections import Counter
import numpy as np
from tqdm import tqdm

def calculate_shannon_entropy(freqs, total_count):
    entropy = 0.0
    for count in freqs.values():
        p = count / total_count
        entropy -= p * math.log2(p)
    return entropy

def fit_zipf_slope(token_counts):
    # Sort frequencies descending
    freqs = sorted(token_counts.values(), reverse=True)
    if len(freqs) < 2:
        return 0.0
    ranks = np.arange(1, len(freqs) + 1)
    
    # Fit line: log(freq) = C - s * log(rank)
    log_ranks = np.log(ranks)
    log_freqs = np.log(freqs)
    
    slope, intercept = np.polyfit(log_ranks, log_freqs, 1)
    return -slope # return s as positive value representing Zipf coefficient

def analyze_corpus(cleaned_dir, output_report_dir, config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    
    os.makedirs(output_report_dir, exist_ok=True)
    
    all_text = []
    documents = []
    source_counts = Counter()
    
    for filename in os.listdir(cleaned_dir):
        if not filename.endswith(".jsonl"):
            continue
            
        path = os.path.join(cleaned_dir, filename)
        print(f"Reading final text from {filename} for analysis...")
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                doc = json.loads(line)
                all_text.append(doc["text"])
                documents.append(doc)
                source_counts[doc["source"]] += len(doc["text"].encode("utf-8"))
                
    if not all_text:
        print("No documents found for analysis!")
        return
        
    combined_text = "\n\n".join(all_text)
    total_bytes = len(combined_text.encode("utf-8"))
    total_chars = len(combined_text)
    
    # Structural splits
    paragraphs = [p for p in combined_text.split("\n\n") if p.strip()]
    lines = [l for l in combined_text.split("\n") if l.strip()]
    
    # Word splitting
    # Replace punctuation with spaces to split words accurately
    clean_word_text = re.sub(r"[^\w\s\u0900-\u097F]", " ", combined_text)
    words = clean_word_text.split()
    word_freqs = Counter(words)
    total_words = len(words)
    unique_words = len(word_freqs)
    
    # Sentence splitting (using danda । and double danda ॥ as separators for Sanskrit, or standard punctuation)
    sentences = re.split(r"[।॥\?\!\.]", combined_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Average lengths
    avg_doc_len = total_chars / len(documents) if documents else 0
    avg_para_len = total_chars / len(paragraphs) if paragraphs else 0
    avg_sentence_len = total_chars / len(sentences) if sentences else 0
    
    # Character entropy
    char_freqs = Counter(combined_text)
    char_entropy = calculate_shannon_entropy(char_freqs, total_chars)
    
    # Tokenizer analysis (train simple BPE tokenizer on final train split)
    print("Training BPE tokenizer for token entropy calculation...")
    from nanochat.tokenizer import RustBPETokenizer
    vocab_size = config.get("vocab_size", 8192)
    # Train only on a subset if corpus is huge to save time
    train_docs = all_text[:20000] if len(all_text) > 20000 else all_text
    tokenizer = RustBPETokenizer.train_from_iterator(train_docs, vocab_size)
    
    print("Encoding final text...")
    tokens = []
    for doc in tqdm(all_text, desc="Tokenizing"):
        tokens.extend(tokenizer.encode(doc))
        
    token_freqs = Counter(tokens)
    total_tokens = len(tokens)
    token_entropy = calculate_shannon_entropy(token_freqs, total_tokens)
    
    # Zipf fit on tokens
    zipf_slope = fit_zipf_slope(token_freqs)
    
    # Vocabulary growth curve (Heaps' Law): vocab size vs token count at 10 intervals
    heaps_points = []
    vocab_tracker = set()
    step_size = max(1, total_tokens // 10)
    for idx, tok in enumerate(tokens):
        vocab_tracker.add(tok)
        if (idx + 1) % step_size == 0 or (idx + 1) == total_tokens:
            heaps_points.append((idx + 1, len(vocab_tracker)))
            
    # Script block distribution
    devanagari_count = len(re.findall(r"[\u0900-\u097F]", combined_text))
    devanagari_ext_count = len(re.findall(r"[\uA8E0-\uA8FF\u1CD0-\u1CFF]", combined_text))
    latin_count = len(re.findall(r"[a-zA-Z]", combined_text))
    digits_count = len(re.findall(r"\d", combined_text))
    punct_count = len(re.findall(r"[^\w\s\u0900-\u097F]", combined_text))
    
    # Load deduplication and filter stats if they exist
    metadata_dir = os.path.join(os.path.dirname(cleaned_dir), "metadata")
    dedup_stats = {}
    if os.path.exists(os.path.join(metadata_dir, "dedup_stats.json")):
        with open(os.path.join(metadata_dir, "dedup_stats.json"), "r") as f:
            dedup_stats = json.load(f)
            
    filter_stats = {}
    if os.path.exists(os.path.join(metadata_dir, "filter_stats.json")):
        with open(os.path.join(metadata_dir, "filter_stats.json"), "r") as f:
            filter_stats = json.load(f)
            
    # Calculate duplicate rates
    total_lines_dedup = dedup_stats.get("lines_removed_local", 0)
    total_lines_original = len(lines) + total_lines_dedup
    line_dup_rate = (total_lines_dedup / total_lines_original * 100) if total_lines_original > 0 else 0.0
    
    # Write report: reports/statistics.md
    stats_md = f"""# Statistics Report

This report summarizes the quantitative parameters of the built dataset.

## Core Dataset Dimensions

| Metric | Value |
| :--- | :--- |
| **Dataset Size (bytes)** | {total_bytes:,} |
| **Documents** | {len(documents):,} |
| **Paragraphs** | {len(paragraphs):,} |
| **Lines** | {len(lines):,} |
| **Unicode Characters** | {total_chars:,} |
| **Total Words** | {total_words:,} |
| **Unique Words (Vocabulary)** | {unique_words:,} |
| **Average Document Length (chars)** | {avg_doc_len:.2f} |
| **Average Paragraph Length (chars)**| {avg_para_len:.2f} |
| **Average Sentence Length (chars)** | {avg_sentence_len:.2f} |

---

## Entropy & Information Density

*   **Character Entropy**: **{char_entropy:.4f} bits/character** (theoretical limit of script predictability).
*   **Token Entropy**: **{token_entropy:.4f} bits/token** (vocabulary size = {vocab_size}).
*   **Zipf Coefficient**: **{zipf_slope:.4f}** (slope of token frequency distribution).

---

## Vocabulary Growth Curve (Heaps' Law)

| Tokens Processed | Unique Tokens (Vocab Size) |
| ---: | ---: |
{chr(10).join([f"| {t:,} | {v:,} |" for t, v in heaps_points])}
"""

    with open(os.path.join(output_report_dir, "statistics.md"), "w") as f:
        f.write(stats_md)
        
    # Write report: reports/quality_report.md
    scores = [doc["quality_score"] for doc in documents]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    quality_md = f"""# Quality Report

This report tracks the evaluation of corpus cleaning heuristics and quality scoring distribution.

## Quality Scores Summary

*   **Average Quality Score**: **{avg_score:.2f} / 100**
*   **Quality Filtering Threshold**: **{config.get('filters', {}).get('quality_threshold', 80)}**
*   **Total Rejected Documents**: **{filter_stats.get('rejected', 0):,}**
*   **Total Accepted Documents**: **{filter_stats.get('accepted', 0):,}**

## Quality Heuristics Diagnostics

*   **Average Devanagari ratio**: **{sans_tok_stats_ratio(documents):.4f}**
*   **Average Punctuation density**: **{punct_count / total_chars:.4f}**
*   **Average Digit density**: **{digits_count / total_chars:.4f}**
"""

    with open(os.path.join(output_report_dir, "quality_report.md"), "w") as f:
        f.write(quality_md)
        
    # Write report: reports/duplicates.md
    duplicates_md = f"""# Duplicates Report

This report documents the multi-level deduplication statistics.

## Deduplication Metrics Table

| Stage | Scanned | Removed | Duplicate Rate (%) |
| :--- | ---: | ---: | ---: |
| **Document-level (Exact)** | {dedup_stats.get('original_docs', 0):,} | {dedup_stats.get('docs_removed_exact', 0):,} | {(dedup_stats.get('docs_removed_exact', 0) / max(1, dedup_stats.get('original_docs', 0)) * 100):.2f}% |
| **Paragraph-level (Global Boilerplate)** | - | {dedup_stats.get('paragraphs_removed_global', 0):,} | - |
| **Line-level (Local Cyclic)** | {total_lines_original:,} | {dedup_stats.get('lines_removed_local', 0):,} | {line_dup_rate:.2f}% |

## Scientific Verification
*   **Success Criterion (Duplicate Line Rate < 2%)**: **{'SUCCESS' if line_dup_rate < 2.0 else 'FAILED'}** (Final line duplication rate: **{line_dup_rate:.4f}%**).
"""

    with open(os.path.join(output_report_dir, "duplicates.md"), "w") as f:
        f.write(duplicates_md)
        
    # Write report: reports/unicode_report.md
    unicode_md = f"""# Unicode Block Report

This report maps the script block distributions and most frequent glyphs in the corpus.

## Script Block Distributions

| Unicode Block | Count | Percentage |
| :--- | ---: | ---: |
| **Devanagari (Sanskrit script)** | {devanagari_count:,} | {(devanagari_count / total_chars * 100):.2f}% |
| **Devanagari Extended (Vedic)** | {devanagari_ext_count:,} | {(devanagari_ext_count / total_chars * 100):.2f}% |
| **Latin (English/Transliterations)**| {latin_count:,} | {(latin_count / total_chars * 100):.2f}% |
| **Digits** | {digits_count:,} | {(digits_count / total_chars * 100):.2f}% |
| **Punctuation & Spaces** | {punct_count:,} | {(punct_count / total_chars * 100):.2f}% |

## Top 15 Most Frequent Characters

| Rank | Character | Count | Frequency (%) |
| ---: | :---: | ---: | ---: |
{chr(10).join([f"| {idx+1} | `{char}` | {count:,} | {(count/total_chars*100):.2f}% |" for idx, (char, count) in enumerate(char_freqs.most_common(15))])}
"""

    with open(os.path.join(output_report_dir, "unicode_report.md"), "w") as f:
        f.write(unicode_md)
        
    # Write report: reports/source_breakdown.md
    source_md = f"""# Source Breakdown

This report tracks data provenance and representation shares.

## Ingested Datasets

| Dataset Source | Bytes (UTF-8) | Percentage Share |
| :--- | ---: | ---: |
{chr(10).join([f"| **{src}** | {size:,} | {(size / total_bytes * 100):.2f}% |" for src, size in source_counts.items()])}
"""

    with open(os.path.join(output_report_dir, "source_breakdown.md"), "w") as f:
        f.write(source_md)
        
    # Write manifest.json data structure for pipeline use
    manifest_data = {
        "version": "SanskritPile-v1",
        "total_documents": len(documents),
        "total_characters": total_chars,
        "total_bytes": total_bytes,
        "duplicate_rate": round(line_dup_rate, 4),
        "sources": dict(source_counts)
    }
    with open(os.path.join(metadata_dir, "manifest_data.json"), "w") as f:
        json.dump(manifest_data, f)
        
    print("Corpus analysis completed and reports written.")

def sans_tok_stats_ratio(documents):
    ratios = [doc["quality_breakdown"]["devanagari_ratio"] for doc in documents]
    return sum(ratios) / len(ratios) if ratios else 0.0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analyze final corpus and generate reports.")
    parser.add_argument("--cleaned_dir", type=str, required=True)
    parser.add_argument("--reports_dir", type=str, required=True)
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    
    analyze_corpus(args.cleaned_dir, args.reports_dir, args.config)
