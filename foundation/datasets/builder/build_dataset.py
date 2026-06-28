import os
import json
import datetime
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

def compile_dataset(cleaned_dir, output_dir, metadata_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    documents = []
    for filename in os.listdir(cleaned_dir):
        if not filename.endswith(".jsonl"):
            continue
            
        path = os.path.join(cleaned_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                documents.append(json.loads(line))
                
    if not documents:
        print("No documents to build dataset from!")
        return
        
    print(f"Compiling {len(documents):,} documents into Parquet shards...")
    
    # 95% train / 5% val split
    split_idx = int(len(documents) * 0.95)
    train_docs = documents[:split_idx]
    val_docs = documents[split_idx:]
    
    def write_shard(docs, filename):
        # We preserve all metadata fields in the Parquet schema!
        texts = [d["text"] for d in docs]
        ids = [d["id"] for d in docs]
        sources = [d["source"] for d in docs]
        download_urls = [d["download_url"] for d in docs]
        licenses = [d["license"] for d in docs]
        titles = [d["title"] for d in docs]
        authors = [d["author"] for d in docs]
        quality_scores = [d["quality_score"] for d in docs]
        
        table = pa.Table.from_pydict({
            "id": ids,
            "text": texts,
            "source": sources,
            "download_url": download_urls,
            "license": licenses,
            "title": titles,
            "author": authors,
            "quality_score": quality_scores
        })
        
        shard_path = os.path.join(output_dir, filename)
        pq.write_table(table, shard_path, row_group_size=1024, compression="zstd")
        print(f"Saved {len(docs):,} documents to {shard_path}.")
        
    write_shard(train_docs, "shard_00000.parquet")
    write_shard(val_docs, "shard_00001.parquet")
    
    # Generate build manifest.json
    manifest_source_path = os.path.join(metadata_dir, "manifest_data.json")
    manifest = {
        "version": "SanskritPile-v1",
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "total_documents": len(documents),
        "total_train_documents": len(train_docs),
        "total_val_documents": len(val_docs)
    }
    
    if os.path.exists(manifest_source_path):
        with open(manifest_source_path, "r") as f:
            source_manifest = json.load(f)
            manifest.update(source_manifest)
            
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Build manifest written to {manifest_path}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compile sharded Parquet files and write manifest.")
    parser.add_argument("--cleaned_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--metadata_dir", type=str, required=True)
    args = parser.parse_args()
    
    compile_dataset(args.cleaned_dir, args.output_dir, args.metadata_dir)
