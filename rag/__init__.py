"""Knowledge mode: turn a pile of personal notes/PDFs/code into grounded answers.

Pipeline (each stage is its own module so it can be tested in isolation):

    ingest  -> load files into Document records with metadata
    chunk   -> split documents into overlapping, heading-aware Chunks
    embed   -> encode text into vectors with a local model (no API)
    store   -> persist vectors + text + metadata in ChromaDB
    retrieve-> embed a query, fetch the nearest chunks
    answer  -> feed retrieved context to the brain for a grounded reply
"""
