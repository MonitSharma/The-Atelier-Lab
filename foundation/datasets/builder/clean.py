import os
import json
import re
from tqdm import tqdm

def clean_document(text, config):
    filters = config.get("filters", {})
    
    # 1. Remove HTML/XML tags
    text = re.sub(r"<[^>]+>", "", text)
    
    # 2. Remove Markdown links and syntax
    # Replace markdown links [text](url) with just text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    if filters.get("remove_headers", True):
        # Strip markdown header hashes
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
        
    # Strip bold/italic formatting characters
    text = re.sub(r"\*\*|__|\*|_", "", text)
    
    # 3. Remove Wikipedia specific elements
    # Edit button markup
    text = re.sub(r"\[\s*सम्पादनं करोतु\s*\]|\[\s*सम्पाद्यताम्\s*\]", "", text)
    # Wikipedia navigation crumbs/boilerplate lines
    wiki_boilerplate_patterns = [
        r"इतः गम्यताम्:\s*सञ्चरणम्,\s*अन्वेषणम्",
        r"मुख्यपृष्ठम्",
        r"सङ्गमनम्",
        r"सद्यःकालीनघटनाः",
        r"नूतनपरिवर्तनानि",
        r"यादृच्छिकपृष्ठम्",
        r"साहाय्यम्",
        r"दानम्"
    ]
    for pattern in wiki_boilerplate_patterns:
        text = re.sub(pattern, "", text)
        
    # 4. Remove GRETIL headers & editorial text
    if filters.get("remove_headers", True):
        text = re.sub(r"(?i)Input by .*?\n|Typed by .*?\n|Text input by .*?\n", "", text)
        text = re.sub(r"(?i)GRETIL Text Files.*?\n", "", text)
        
    # 5. Remove page numbers
    text = re.sub(r"\[\s*(?:पृष्ठम्|Page|page|p\.)\s*\d+\s*\]", "", text)
    
    # 6. Remove TOC dot fragments
    text = re.sub(r"\.{4,}", "", text)
    
    # Post-clean: strip empty spaces and lines
    lines = [line.strip() for line in text.split("\n")]
    # Remove lines that are purely symbols or blank
    cleaned_lines = []
    for line in lines:
        if line:
            # Collapse multiple spaces created during cleaning
            line_clean = re.sub(r"[ \t]+", " ", line).strip()
            # Check if line contains only spaces, hyphens, or symbols
            if line_clean and not re.match(r"^[-\s_=\+\*#\\/\|\d]+$", line_clean):
                cleaned_lines.append(line_clean)
                
    return "\n".join(cleaned_lines).strip()

def clean_directory(input_dir, output_dir, config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
        
    os.makedirs(output_dir, exist_ok=True)
    
    for filename in os.listdir(input_dir):
        if not filename.endswith(".jsonl"):
            continue
            
        in_path = os.path.join(input_dir, filename)
        out_path = os.path.join(output_dir, f"cleaned_{filename.replace('normalized_', '')}")
        
        print(f"Cleaning {filename}...")
        count = 0
        with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
            for line in tqdm(fin, desc="Cleaning documents"):
                doc = json.loads(line)
                doc["text"] = clean_document(doc["text"], config)
                doc["pipeline_steps"].append("cleaned")
                fout.write(json.dumps(doc, ensure_ascii=False) + "\n")
                count += 1
                
        print(f"Cleaned {count} docs from {filename} to {out_path}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Clean HTML, OCR noise, and headers/footers.")
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    
    clean_directory(args.input_dir, args.output_dir, args.config)
