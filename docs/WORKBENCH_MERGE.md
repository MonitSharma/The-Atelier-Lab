# Atelier Workbench merge

`The-Atelier-Lab/atelier_agent` is the canonical application. The standalone
`~/atelier-workbench` remains a reference prototype; its validated ideas were
integrated without introducing a second CLI, virtual environment, or LanceDB
runtime.

## Integrated

- LFM2.5-2.6B Q6_K is now the default worker role.
- Qwen3-Embedding-4B through Ollama is now the default embedding backend.
- The validated instruction-aware scientific query format is applied only to
  queries; document passages remain unmodified.
- PDFs use the scientific page/section-aware adapter with SHA-256 document IDs,
  page metadata, section metadata, and 1,800/250-character paper chunks.
- Fast Paper characterization is cached in `data/paper_metadata/` by content
  hash and exposed through `atelier paper PATH`.
- `atelier search QUERY` exposes retrieval without synthesis.
- Re-ingestion replaces a source's existing chunks, preventing stale tail
  chunks after a document changes.
- A SQLite manifest now records content identity, paths, chunk counts, index
  schema, and embedding compatibility state; unchanged files are skipped.
- A separate memory manifest and timestamped backup workflow support safe
  re-embedding without deleting the prior memory collection first.

## Preserved from the existing application

- Typer CLI and model-role routing.
- ChromaDB as the vector store for knowledge and memory.
- Dense retrieval, BM25, Reciprocal Rank Fusion, and optional reranking.
- Existing agent, memory, MCP, and evaluation infrastructure.

## Local prototype corpus

The three prototype PDFs and their SHA-keyed metadata were copied into:

```text
atelier_agent/data/corpus/papers/
atelier_agent/data/paper_metadata/
```

These are local runtime artifacts and are intentionally ignored by Git.

## Embedding migration note

Existing Chroma records created with BGE embeddings must be rebuilt before
using Qwen vectors in that collection. Run `atelier ingest --reset ...` for the
knowledge index after the project dependencies and Ollama models are installed.
Existing semantic memory can be migrated safely with `atelier memory-migrate`;
the command writes a timestamped JSON backup and activates a verified new
collection without deleting the old collection first.
