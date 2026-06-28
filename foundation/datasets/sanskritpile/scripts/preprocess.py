import os
import re
from collections import Counter
import pyarrow as pa
import pyarrow.parquet as pq
import torch
from datasets import load_dataset
from nanochat.tokenizer import RustBPETokenizer

TARGET_BYTES = 52_428_800 # 50 MB in bytes

# Cache directories
DATA_ROOT = "/Users/monitsharma/.cache/nanochat"
SANSKRIT_DATA_DIR = os.path.join(DATA_ROOT, "sanskrit_data")
ENGLISH_BYTE_DATA_DIR = os.path.join(DATA_ROOT, "english_data_byte")
ENGLISH_CHAR_DATA_DIR = os.path.join(DATA_ROOT, "english_data_char")

SANSKRIT_TOK_DIR = os.path.join(DATA_ROOT, "tokenizer_sanskrit")
ENGLISH_BYTE_TOK_DIR = os.path.join(DATA_ROOT, "tokenizer_english_byte")
ENGLISH_CHAR_TOK_DIR = os.path.join(DATA_ROOT, "tokenizer_english_char")

os.makedirs(SANSKRIT_DATA_DIR, exist_ok=True)
os.makedirs(ENGLISH_BYTE_DATA_DIR, exist_ok=True)
os.makedirs(ENGLISH_CHAR_DATA_DIR, exist_ok=True)

os.makedirs(SANSKRIT_TOK_DIR, exist_ok=True)
os.makedirs(ENGLISH_BYTE_TOK_DIR, exist_ok=True)
os.makedirs(ENGLISH_CHAR_TOK_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Clean text functions
# -----------------------------------------------------------------------------
def clean_sanskrit_text(text):
    """
    Cleans Sanskrit text by filtering out lines containing English markup, urls,
    transliteration metadata, and keeping only lines containing Devanagari script.
    """
    lines = text.split('\n')
    cleaned_lines = []
    # Devanagari character range regex: \u0900 to \u097F
    devanagari_regex = re.compile(r"[\u0900-\u097F]")
    url_regex = re.compile(r"https?://\S+|www\.\S+")
    html_regex = re.compile(r"<[^>]+>")
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        # Remove URLs and HTML markup
        if url_regex.search(line_strip) or html_regex.search(line_strip):
            continue
        # Keep if it contains Devanagari and doesn't contain Latin characters (indicative of transliteration or metadata)
        if devanagari_regex.search(line_strip) and not re.search(r"[a-zA-Z]", line_strip):
            cleaned_lines.append(line_strip)
            
    return "\n".join(cleaned_lines)

def clean_english_text(text):
    """
    Cleans English text by removing common tags and URLs.
    """
    lines = text.split('\n')
    cleaned_lines = []
    url_regex = re.compile(r"https?://\S+|www\.\S+")
    html_regex = re.compile(r"<[^>]+>")
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
        if url_regex.search(line_strip) or html_regex.search(line_strip):
            continue
        cleaned_lines.append(line_strip)
        
    return "\n".join(cleaned_lines)

# -----------------------------------------------------------------------------
# 1. Download & Process Sanskrit Corpus
# -----------------------------------------------------------------------------
print("=== Collecting Sanskrit Text ===")
sanskrit_accumulator = []
sanskrit_bytes = 0

# Load datasets in streaming mode for speed and memory efficiency
sans_data_ds = load_dataset("saucam/sans_data", split="train", streaming=True)
henil_ds = load_dataset("Henil1/sanskrit", split="train", streaming=True)

# First process henil_ds
print("Gathering from Henil1/sanskrit...")
for item in henil_ds:
    cleaned = clean_sanskrit_text(item["text"])
    if cleaned:
        cleaned_bytes = cleaned.encode("utf-8")
        sanskrit_accumulator.append(cleaned)
        sanskrit_bytes += len(cleaned_bytes)
    if sanskrit_bytes >= TARGET_BYTES:
        break

# Gather more from sans_data_ds
if sanskrit_bytes < TARGET_BYTES:
    print("Gathering from saucam/sans_data...")
    for item in sans_data_ds:
        content = item.get("text")
        if not content:
            continue
        cleaned = clean_sanskrit_text(content)
        if cleaned:
            cleaned_bytes = cleaned.encode("utf-8")
            sanskrit_accumulator.append(cleaned)
            sanskrit_bytes += len(cleaned_bytes)
        if sanskrit_bytes >= TARGET_BYTES:
            break

sanskrit_raw_text = "\n".join(sanskrit_accumulator)
sanskrit_raw_bytes = sanskrit_raw_text.encode("utf-8")
sanskrit_raw_bytes_trimmed = sanskrit_raw_bytes[:TARGET_BYTES]
sanskrit_text = sanskrit_raw_bytes_trimmed.decode("utf-8", errors="ignore")
sanskrit_final_bytes = len(sanskrit_text.encode("utf-8"))
sanskrit_chars = len(sanskrit_text)

print(f"Sanskrit collected: {sanskrit_final_bytes} bytes, {sanskrit_chars} characters")

# -----------------------------------------------------------------------------
# 2. Download & Process English Corpora
# -----------------------------------------------------------------------------
print("\n=== Collecting English Text ===")
english_accumulator = []
english_bytes = 0

english_ds = load_dataset("HuggingFaceFW/fineweb-edu", name="sample-10BT", split="train", streaming=True)

# We gather enough for the byte-matched target (50MB) first
for item in english_ds:
    cleaned = clean_english_text(item["text"])
    if cleaned:
        cleaned_bytes = cleaned.encode("utf-8")
        english_accumulator.append(cleaned)
        english_bytes += len(cleaned_bytes)
    if english_bytes >= TARGET_BYTES:
        break

english_raw_text = "\n".join(english_accumulator)
english_raw_bytes = english_raw_text.encode("utf-8")

# English Byte-Matched (exactly 50MB)
english_byte_bytes_trimmed = english_raw_bytes[:TARGET_BYTES]
english_byte_text = english_byte_bytes_trimmed.decode("utf-8", errors="ignore")
english_byte_final_bytes = len(english_byte_text.encode("utf-8"))
english_byte_chars = len(english_byte_text)
print(f"English Byte-Matched: {english_byte_final_bytes} bytes, {english_byte_chars} characters")

# English Character-Matched (exactly matched to Sanskrit character count: sanskrit_chars)
# Since English is ASCII, 1 character = 1 byte, so we take sanskrit_chars bytes
english_char_bytes_trimmed = english_raw_bytes[:sanskrit_chars]
english_char_text = english_char_bytes_trimmed.decode("utf-8", errors="ignore")
english_char_final_bytes = len(english_char_text.encode("utf-8"))
english_char_chars = len(english_char_text)
print(f"English Character-Matched: {english_char_final_bytes} bytes, {english_char_chars} characters")

# -----------------------------------------------------------------------------
# 3. Quality Analysis
# -----------------------------------------------------------------------------
def analyze_corpus_quality(text, name):
    lines = [l for l in text.split('\n') if l.strip()]
    total_chars = len(text)
    
    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
    latin_chars = len(re.findall(r"[a-zA-Z]", text))
    digits_punct = len(re.findall(r"[\d\W_]", text))
    
    pct_devanagari = (devanagari_chars / total_chars) * 100 if total_chars > 0 else 0
    pct_latin = (latin_chars / total_chars) * 100 if total_chars > 0 else 0
    pct_digits_punct = (digits_punct / total_chars) * 100 if total_chars > 0 else 0
    
    duplicate_line_rate = ((len(lines) - len(set(lines))) / len(lines) * 100) if len(lines) > 0 else 0
    avg_line_len = sum(len(l) for l in lines) / len(lines) if len(lines) > 0 else 0
    
    line_counts = Counter(lines)
    top_repeated = line_counts.most_common(5)
    
    return {
        "pct_devanagari": pct_devanagari,
        "pct_latin": pct_latin,
        "pct_digits_punct": pct_digits_punct,
        "duplicate_line_rate": duplicate_line_rate,
        "avg_line_len": avg_line_len,
        "top_repeated": top_repeated,
        "lines_count": len(lines)
    }

print("\n=== Performing Corpus Quality Checks ===")
sans_qual = analyze_corpus_quality(sanskrit_text, "Sanskrit")
eng_byte_qual = analyze_corpus_quality(english_byte_text, "English Byte-Matched")
eng_char_qual = analyze_corpus_quality(english_char_text, "English Character-Matched")

# -----------------------------------------------------------------------------
# 4. Partition and Shard Datasets
# -----------------------------------------------------------------------------
def split_and_shard(text, output_dir):
    text_utf8 = text.encode("utf-8")
    total_len = len(text_utf8)
    train_split_bytes = int(total_len * 0.95)
    
    train_utf8 = text_utf8[:train_split_bytes]
    val_utf8 = text_utf8[train_split_bytes:]
    
    train_text = train_utf8.decode("utf-8", errors="ignore")
    val_text = val_utf8.decode("utf-8", errors="ignore")
    
    train_docs = [line for line in train_text.split('\n') if line.strip()]
    val_docs = [line for line in val_text.split('\n') if line.strip()]
    
    # Write Parquet shards
    train_table = pa.Table.from_pydict({"text": train_docs})
    pq.write_table(train_table, os.path.join(output_dir, "shard_00000.parquet"), row_group_size=1024, compression="zstd")
    
    val_table = pa.Table.from_pydict({"text": val_docs})
    pq.write_table(val_table, os.path.join(output_dir, "shard_00001.parquet"), row_group_size=1024, compression="zstd")
    
    return train_docs, val_docs

sans_train_docs, sans_val_docs = split_and_shard(sanskrit_text, SANSKRIT_DATA_DIR)
eng_byte_train_docs, eng_byte_val_docs = split_and_shard(english_byte_text, ENGLISH_BYTE_DATA_DIR)
eng_char_train_docs, eng_char_val_docs = split_and_shard(english_char_text, ENGLISH_CHAR_DATA_DIR)

# -----------------------------------------------------------------------------
# 5. Tokenizer Training and Analysis
# -----------------------------------------------------------------------------
def train_and_analyze_tokenizer(train_docs, val_docs, tok_dir, lang_name):
    # Train BPE Tokenizer only on the train split
    tokenizer = RustBPETokenizer.train_from_iterator(train_docs, 32768)
    tokenizer.save(tok_dir)
    
    # Save token_bytes.pt
    vocab_size = tokenizer.get_vocab_size()
    special_set = set(tokenizer.get_special_tokens())
    token_strings = [tokenizer.decode([token_id]) for token_id in range(vocab_size)]
    token_bytes = []
    
    for token_id in range(vocab_size):
        token_str = token_strings[token_id]
        if token_str in special_set:
            token_bytes.append(0)
        else:
            token_bytes.append(len(token_str.encode("utf-8")))
            
    token_bytes_tensor = torch.tensor(token_bytes, dtype=torch.int32, device="cpu")
    with open(os.path.join(tok_dir, "token_bytes.pt"), "wb") as f:
        torch.save(token_bytes_tensor, f)
        
    # Analyze BPE usage
    train_tokens = [tokenizer.encode(doc) for doc in train_docs]
    flat_tokens = [tok for doc in train_tokens for tok in doc]
    
    # Vocab utilization
    unique_toks_seen = set(flat_tokens)
    vocab_util = (len(unique_toks_seen) / vocab_size) * 100
    
    # Unique token ratio
    unique_token_ratio = len(unique_toks_seen) / len(flat_tokens) if len(flat_tokens) > 0 else 0
    
    # Token frequency
    token_freqs = Counter(flat_tokens)
    frequency_one = sum(1 for tok, count in token_freqs.items() if count == 1)
    
    # Mass calculations
    sorted_counts = sorted(token_freqs.values(), reverse=True)
    total_token_count = sum(sorted_counts)
    
    def get_mass_size(pct):
        target_mass = total_token_count * pct
        cumulative_mass = 0
        for idx, count in enumerate(sorted_counts):
            cumulative_mass += count
            if cumulative_mass >= target_mass:
                return idx + 1
        return len(sorted_counts)
        
    mass_1 = get_mass_size(0.01)
    mass_10 = get_mass_size(0.10)
    mass_50 = get_mass_size(0.50)
    
    total_bytes = sum(len(doc.encode("utf-8")) for doc in train_docs + val_docs)
    total_chars = sum(len(doc) for doc in train_docs + val_docs)
    total_tokens = sum(len(tokenizer.encode(doc)) for doc in train_docs + val_docs)
    
    return {
        "bytes": total_bytes,
        "chars": total_chars,
        "tokens": total_tokens,
        "bytes_per_tok": total_bytes / total_tokens,
        "chars_per_tok": total_chars / total_tokens,
        "unique_tok_ratio": unique_token_ratio,
        "vocab_util": vocab_util,
        "frequency_one": frequency_one,
        "mass_1": mass_1,
        "mass_10": mass_10,
        "mass_50": mass_50
    }

print("\n=== Training and Analyzing BPE Tokenizers ===")
sans_tok_stats = train_and_analyze_tokenizer(sans_train_docs, sans_val_docs, SANSKRIT_TOK_DIR, "Sanskrit")
eng_byte_tok_stats = train_and_analyze_tokenizer(eng_byte_train_docs, eng_byte_val_docs, ENGLISH_BYTE_TOK_DIR, "English-Byte")
eng_char_tok_stats = train_and_analyze_tokenizer(eng_char_train_docs, eng_char_val_docs, ENGLISH_CHAR_TOK_DIR, "English-Char")

# -----------------------------------------------------------------------------
# 6. Generate reports
# -----------------------------------------------------------------------------
tok_report = f"""# Tokenizer Efficiency and Vocabulary Report

This document reports the comparative statistics and vocabulary details of custom BPE tokenizers (vocab = 32,768) trained on matched splits.

## BPE Optimization Table

| Corpus | Raw Bytes | Unicode Chars | Lines | Vocab | Tokens | Bytes/token | Chars/token | Unique Token Ratio |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **English-Byte** | {eng_byte_tok_stats['bytes']:,} | {eng_byte_tok_stats['chars']:,} | {eng_byte_qual['lines_count']:,} | 32,768 | {eng_byte_tok_stats['tokens']:,} | {eng_byte_tok_stats['bytes_per_tok']:.4f} | {eng_byte_tok_stats['chars_per_tok']:.4f} | {eng_byte_tok_stats['unique_tok_ratio']:.4f} |
| **Sanskrit** | {sans_tok_stats['bytes']:,} | {sans_tok_stats['chars']:,} | {sans_qual['lines_count']:,} | 32,768 | {sans_tok_stats['tokens']:,} | {sans_tok_stats['bytes_per_tok']:.4f} | {sans_tok_stats['chars_per_tok']:.4f} | {sans_tok_stats['unique_tok_ratio']:.4f} |
| **English-Char** | {eng_char_tok_stats['bytes']:,} | {eng_char_tok_stats['chars']:,} | {eng_char_qual['lines_count']:,} | 32,768 | {eng_char_tok_stats['tokens']:,} | {eng_char_tok_stats['bytes_per_tok']:.4f} | {eng_char_tok_stats['chars_per_tok']:.4f} | {eng_char_tok_stats['unique_tok_ratio']:.4f} |

## Vocabulary Utilization & Sparsity Checks

Because the dataset sizes are relatively small (19.3MB–50MB), some BPE vocabulary entries may remain sparse or completely unused.

| Metric | English-Byte | Sanskrit | English-Char |
| :--- | :--- | :--- | :--- |
| **Vocab Utilization (%)** | {eng_byte_tok_stats['vocab_util']:.2f}% | {sans_tok_stats['vocab_util']:.2f}% | {eng_char_tok_stats['vocab_util']:.2f}% |
| **Tokens with Frequency = 1** | {eng_byte_tok_stats['frequency_one']:,} | {sans_tok_stats['frequency_one']:,} | {eng_char_tok_stats['frequency_one']:,} |
| **Top 1% Token Mass** | {eng_byte_tok_stats['mass_1']:,} tokens | {sans_tok_stats['mass_1']:,} tokens | {eng_char_tok_stats['mass_1']:,} tokens |
| **Top 10% Token Mass** | {eng_byte_tok_stats['mass_10']:,} tokens | {sans_tok_stats['mass_10']:,} tokens | {eng_char_tok_stats['mass_10']:,} tokens |
| **Top 50% Token Mass** | {eng_byte_tok_stats['mass_50']:,} tokens | {sans_tok_stats['mass_50']:,} tokens | {eng_char_tok_stats['mass_50']:,} tokens |
"""

with open("/Users/monitsharma/code_projects/The-Atelier-Lab/foundation/experiments/002_sanskrit_vs_english_pilot/tokenizer_report.md", "w") as f:
    f.write(tok_report)

data_sources_report = f"""# Data Sources and Quality Report

This document reports the quality diagnostics of the Sanskrit and English corpora.

## Diagnostic Metrics Table

| Metric | Sanskrit | English-Byte | English-Char |
| :--- | :--- | :--- | :--- |
| **Percent Devanagari Characters** | {sans_qual['pct_devanagari']:.2f}% | {eng_byte_qual['pct_devanagari']:.2f}% | {eng_char_qual['pct_devanagari']:.2f}% |
| **Percent Latin Characters** | {sans_qual['pct_latin']:.2f}% | {eng_byte_qual['pct_latin']:.2f}% | {eng_char_qual['pct_latin']:.2f}% |
| **Percent Digits/Punctuation** | {sans_qual['pct_digits_punct']:.2f}% | {eng_byte_qual['pct_digits_punct']:.2f}% | {eng_char_qual['pct_digits_punct']:.2f}% |
| **Duplicate Line Rate** | {sans_qual['duplicate_line_rate']:.2f}% | {eng_byte_qual['duplicate_line_rate']:.2f}% | {eng_char_qual['duplicate_line_rate']:.2f}% |
| **Average Line Length (chars)** | {sans_qual['avg_line_len']:.2f} | {eng_byte_qual['avg_line_len']:.2f} | {eng_char_qual['avg_line_len']:.2f} |

### Top 5 Repeated Lines (Sanskrit)
{chr(10).join([f"- **{count} times**: `{line}`" for line, count in sans_qual['top_repeated']])}
"""

with open("/Users/monitsharma/code_projects/The-Atelier-Lab/foundation/experiments/002_sanskrit_vs_english_pilot/data_sources.md", "w") as f:
    f.write(data_sources_report)

print("Pre-processing reports successfully written.")
