import os
import argparse
import sys
import logging
import shutil

from foundation.datasets.builder.download import download_corpora
from foundation.datasets.builder.normalize import normalize_directory
from foundation.datasets.builder.clean import clean_directory
from foundation.datasets.builder.deduplicate import deduplicate_directory
from foundation.datasets.builder.filter import filter_directory
from foundation.datasets.builder.analyze import analyze_corpus
from foundation.datasets.builder.build_dataset import compile_dataset

def setup_logger(metadata_dir):
    os.makedirs(metadata_dir, exist_ok=True)
    log_path = os.path.join(metadata_dir, "pipeline.log")
    
    logger = logging.getLogger("DatasetBuilder")
    logger.setLevel(logging.INFO)
    
    # Reset existing handlers if any
    if logger.handlers:
        logger.handlers.clear()
        
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(console_handler)
    
    return logger

def run_pipeline(project_dir, config_path, download_limit=None, max_bytes=55_000_000, cleanup=True):
    raw_dir = os.path.join(project_dir, "raw")
    intermediate_dir = os.path.join(project_dir, "intermediate")
    normalized_dir = os.path.join(intermediate_dir, "normalized")
    cleaned_dir = os.path.join(intermediate_dir, "cleaned")
    deduped_dir = os.path.join(intermediate_dir, "deduplicated")
    
    final_cleaned_dir = os.path.join(project_dir, "cleaned")
    metadata_dir = os.path.join(project_dir, "metadata")
    reports_dir = os.path.join(project_dir, "reports")
    final_dataset_dir = os.path.join(project_dir, "SanskritPile-v1")
    
    logger = setup_logger(metadata_dir)
    logger.info("Starting SanskritPile-v1 Pretraining Dataset Build Pipeline")
    logger.info(f"Project directory: {project_dir}")
    logger.info(f"Config path: {config_path}")
    logger.info(f"Max bytes limit: {max_bytes:,}")
    if download_limit:
        logger.info(f"Download limit set to: {download_limit}")
        
    try:
        # 1. Download
        logger.info("=== STAGE 1: Downloading raw corpora ===")
        download_corpora(raw_dir, limit=download_limit, max_bytes=max_bytes)
        
        # 2. Normalize
        logger.info("=== STAGE 2: Normalizing Unicode and whitespace ===")
        normalize_directory(raw_dir, normalized_dir)
        
        # 3. Clean
        logger.info("=== STAGE 3: Cleaning headers, footers, HTML, and OCR patterns ===")
        clean_directory(normalized_dir, cleaned_dir, config_path)
        
        # 4. Deduplicate
        logger.info("=== STAGE 4: Running multi-level exact deduplication ===")
        deduplicate_directory(cleaned_dir, deduped_dir, config_path)
        
        # 5. Filter
        logger.info("=== STAGE 5: Quality scoring and document filtering ===")
        filter_directory(deduped_dir, final_cleaned_dir, config_path)
        
        # 6. Analyze
        logger.info("=== STAGE 6: Performing corpus statistics and entropy analysis ===")
        analyze_corpus(final_cleaned_dir, reports_dir, config_path)
        
        # 7. Build Dataset
        logger.info("=== STAGE 7: Building final sharded Parquet dataset & manifest ===")
        compile_dataset(final_cleaned_dir, final_dataset_dir, metadata_dir)
        
        # 8. Cleanup Intermediate Folders
        if cleanup:
            logger.info("=== STAGE 8: Reclaiming disk space by cleaning up raw & intermediate files ===")
            shutil.rmtree(raw_dir, ignore_errors=True)
            shutil.rmtree(intermediate_dir, ignore_errors=True)
            shutil.rmtree(final_cleaned_dir, ignore_errors=True)
            logger.info("Raw and intermediate JSONL folders successfully cleaned.")
            
        logger.info("=== Pipeline Completed Successfully! ===")
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the pretraining dataset pipeline.")
    parser.add_argument("--project_dir", type=str, required=True, help="Path to project directory (e.g. foundation/datasets/sanskritpile).")
    parser.add_argument("--config", type=str, required=True, help="Path to pipeline configuration json.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of documents downloaded per corpus for rapid test builds.")
    parser.add_argument("--max_bytes", type=int, default=55000000, help="Max raw text bytes to download across all corpora.")
    parser.add_argument("--no_cleanup", action="store_true", help="Prevent automatic deletion of raw/intermediate folders.")
    args = parser.parse_args()
    
    run_pipeline(args.project_dir, args.config, args.limit, args.max_bytes, cleanup=not args.no_cleanup)
