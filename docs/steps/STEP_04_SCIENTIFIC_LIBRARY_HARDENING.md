# Step 04 — Scientific Library Hardening

## Freeze report

Status: **PASS — Scientific Library v1.0 can be frozen locally.**

This report records the implementation and verification of the merged Atelier
scientific research library. It is intentionally separate from the historical
LFM and Qwen embedding benchmark reports.

## 1. Objective

Harden the merged Atelier Workbench into one stable local research library
while preserving its existing Typer CLI, persistent session, Ollama runtime,
ChromaDB store, dense retrieval, BM25, RRF, optional reranking, ReAct agent,
MCP, semantic memory, and evaluation infrastructure.

The milestone makes PDF ingestion content-addressed and incremental, metadata
scientifically useful, LFM output schema-safe, retrieval section-aware,
embedding compatibility explicit, memory migration safe, and the CLI
reproducible.

## 2. Baseline state

Before hardening, the local checkout was on
`refactor/learning-first-reorganization`. The merged prototype already had:

- LFM2.5-2.6B Q6_K as the worker;
- Qwen3-Embedding-4B through Ollama;
- a 2,560-dimensional Chroma index;
- three local PDFs and 231 stored chunks;
- a compact terminal banner and persistent session;
- prototype SHA metadata, but no general SQLite manifest;
- path-oriented incremental behavior rather than a complete content-addressed
  plan;
- flat legacy paper metadata;
- generic `format="json"` rather than provider-level JSON Schema support;
- no friendly vector-index compatibility guard;
- no safe memory migration workflow.

The local corpus is:

```text
atelier_agent/data/corpus/papers/
├── Data-Driven Newsvendor Problem.pdf
├── qshield.pdf
└── tail_risk.pdf
```

## 3. Problems discovered

1. A renamed file could be treated as a new source even though its content was
   unchanged.
2. Modified files could leave stale tail chunks because Chroma upsert does not
   remove old chunk IDs automatically.
3. Removed files were not represented explicitly in an ingest plan.
4. Chroma records did not record the embedding model or dimension in a durable
   manifest.
5. PDF extraction artifacts, including picture placeholders and picture-text
   blocks, leaked into retrieval results.
6. Existing paper metadata mixed objective identity, subjective relevance, and
   filesystem location.
7. The LFM provider could request generic JSON but could not pass an Ollama
   JSON Schema.
8. RRF could return reference chunks ahead of substantive sections for broad
   conceptual queries.
9. Memory shared the embedding store but had no backup/re-embedding migration.
10. `doctor` treated an empty optional model slot as a missing model and could
    print an invalid empty pull command.
11. Rich could interpret arbitrary retrieved scientific text as markup.

## 4. Architecture before

```text
files → generic chunker → sentence-transformers/Ollama embedder → Chroma
                                                        ↓
                                             dense + BM25/RRF retrieval
```

PDFs were already using the better PyMuPDF4LLM prototype adapter, but the
adapter, metadata cache, Chroma state, and filesystem identity were not yet
coordinated by one manifest.

## 5. Architecture after

```text
explicit roots
    ↓
SQLite manifest plan (SHA-256, path, state, aliases)
    ├── unchanged       → no extraction, no embedding
    ├── relocated       → update locator, reuse vectors
    ├── duplicate       → register alias, reuse vectors
    ├── new/modified    → extract → chunk → embed → replace
    └── sync removal    → explicit deletion only
              ↓
PDF → cached raw + cleaned page text → section-aware chunks
              ↓
Qwen3-Embedding-4B / 2560D → ChromaDB
              ↓
dense + BM25 + RRF → section adjustment → diversity → optional reranker
```

The existing application remains canonical. No second CLI, LanceDB database,
LangGraph layer, cloud API, or new model tier was added.

## 6. Incremental indexing design

`atelier ingest PATH...` now supports:

```text
--force     re-extract and re-embed discovered files
--dry-run   print the plan without changing Chroma or the manifest
--sync      reconcile missing files under explicitly supplied roots
--reset     explicitly reset the knowledge collection and manifest
```

Normal states are `unchanged`, `new`, `modified`, `relocated`, `duplicate`,
and `removed`. Ordinary ingestion never silently removes missing files.

New and modified records are extracted and embedded first. The replacement is
then upserted; stale chunks are removed only after the replacement vectors are
available. Forced replacement uses `VectorStore.replace_document`, which
removes old tail IDs after the new chunks have been upserted.

The final real dry-run reported:

```text
unchanged 3
new       0
modified  0
relocated 0
duplicate 0
forced    0
removed   0
```

The existing 2,560D index was bootstrapped into the new manifest without
re-embedding, then forced once to apply the conservative extraction cleanup.
The resulting Chroma count is 223, matching the manifest counts of 64, 89,
and 70 chunks for the three papers.

## 7. SQLite manifest schema

Implemented in `rag/manifest.py` using only the Python standard library.

```text
documents(
  document_id PRIMARY KEY,
  current_path,
  filename,
  size_bytes,
  mtime_ns,
  chunk_count,
  indexed_at,
  updated_at,
  doc_type,
  metadata_schema_version
)

document_paths(document_id, path, is_current, seen_at)
index_state(key PRIMARY KEY, value)
```

Runtime location:

```text
atelier_agent/data/index_manifest.sqlite3
```

The manifest records `qwen3-embedding:4b`, dimension `2560`, index schema 1,
and chunk schema 2 after the local rebuild.

## 8. Content identity rules

Every supported Markdown, text, code, and PDF file receives a SHA-256
`document_id`. Absolute paths are locators only. Chunk IDs derive from
`document_id:chunk_index` rather than an absolute path.

An exact rename reuses the vectors and updates the source locator. An exact
duplicate registers a path alias. Changed content receives a new ID and
replaces the previous document only after new vectors are prepared.

The injected fake-embedder regression suite verifies:

```text
first ingest       1 embedding call
unchanged ingest   0 additional calls
rename             0 additional calls; same document_id
modification       1 additional call; new document_id
duplicate          0 additional calls
ordinary removal  no deletion
--sync removal    explicit reconciliation
--dry-run         no manifest/store/embedder changes
```

## 9. PDF extraction and cleanup rules

`rag/paper.py` now caches content-addressed page extraction in:

```text
atelier_agent/data/extracted/<document_id>.json
```

Each page retains both `raw_text` and retrieval `text`. Cleanup is
conservative: it removes explicit PyMuPDF4LLM picture-placeholder boilerplate,
picture-text blocks, `<br>` tags, NUL/replacement-character noise, and obvious
repeated whitespace. It does not rewrite equations, infer missing symbols, or
delete references.

The local extraction cache contains 3 entries after the real corpus rebuild.

## 10. Metadata schema

Paper metadata is cached by SHA in:

```text
atelier_agent/data/paper_metadata/<document_id>.json
```

The current structure is:

```json
{
  "schema_version": 2,
  "document_id": "...",
  "identity": {
    "title": "...",
    "authors": [],
    "year": "",
    "doi": "",
    "arxiv_id": "",
    "document_type": "research_paper",
    "domain": "",
    "venue": ""
  },
  "characterization": {
    "paper_type": "...",
    "subfields": [],
    "research_problem": "...",
    "method": "...",
    "main_claim": "...",
    "theoretical": false,
    "experimental": false,
    "ai_relevance": "none",
    "quantum_relevance": "none",
    "optimization_relevance": "none",
    "why_relevant": "...",
    "recommended_action": "skim",
    "confidence": "low"
  }
}
```

Filesystem path and filename are not scientific identity. Legacy identity-only
caches are accepted for chunk metadata but are upgraded when `atelier paper`
needs a complete characterization card. Identifier-shaped hallucinations in
the arXiv field are conservatively cleared rather than cached as facts.

## 11. Strict LFM schema implementation

`PaperIdentity`, `PaperCharacterization`, and `PaperExtraction` are strict
Pydantic models with forbidden extra fields, required fields, controlled enums,
and boolean fields. `agent.brain.chat` and the provider protocol now accept an
optional `json_schema`. `OllamaProvider` passes that object as the Ollama
`format` value while preserving generic `json_mode=True` behavior.

Malformed output raises a useful error and is not written to the cache. Tests
cover required fields, unexpected fields, and provider schema forwarding.

The real local characterization was run once for the Newsvendor paper after
the legacy identity cache was detected. The second invocation was cache-backed
and measured 0.17 seconds.

## 12. Retrieval architecture

The production retrieval path remains:

```text
Qwen3-Embedding-4B dense retrieval
        + BM25 lexical retrieval
        → Reciprocal Rank Fusion
        → section-aware score adjustment
        → deterministic diversity selection
        → optional cross-encoder reranking
```

The candidate pool is assembled at `hybrid_candidates` size before final
selection. BM25 cache invalidation now fingerprints document content rather
than checking only the number of chunks.

## 13. Section-aware ranking logic

The final resolved raw section title is preserved and mapped to:

```text
front_matter, abstract, introduction, related_work, methods, theory,
experiments, results, discussion, conclusion, references, appendix, other
```

For normal concept queries, references receive a modest deterministic penalty
and substantive sections receive a small preference. References are never
excluded. For explicit reference/literature/citation/source queries, references
and related work receive a boost.

After score adjustment, the selector limits repeated document/section pairs
before using deferred candidates to fill the requested k.

## 14. Reference intent

Reference intent detects terms such as `references`, `bibliography`, `citations`,
`cited`, `papers`, `prior`, `related`, `literature`, and `sources`.

The real literature query returned a References result at rank 1 while the
normal `quantum` query returned conceptual sections in its top three and
references only lower down.

## 15. Diversity logic

Diversity is deterministic and local: it tracks `(document_id, section_type)`
pairs, selects one strong result from a pair first, then uses deferred results
when necessary. It does not force unrelated sources into the result set.

## 16. Memory migration design

Semantic memory has its own SQLite state manifest and active collection name.
`atelier memory-migrate`:

1. reads all records and preserves IDs, text, tags, and timestamps;
2. writes a timestamped JSON backup before changing active state;
3. embeds records with the current embedder;
4. writes a new Chroma collection;
5. verifies the count;
6. activates the new collection without deleting the old collection first.

The real migration preserved 3 facts before and after and wrote:

```text
atelier_agent/data/memory_backups/memory-20260809T133830Z.json
```

`doctor` now reports memory as Qwen3-Embedding-4B / 2,560D, and recall was
verified after migration.

## 17. Doctor/status changes

`atelier doctor` now distinguishes:

- configured and installed models: `ok`;
- configured but missing models: `missing`;
- empty optional expert slot: `unconfigured`.

The final local status was:

```text
worker       ok          hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q6_K
brain        missing     qwen3:14b
router       missing     qwen3:4b
expert       unconfigured
knowledge    compatible  223 chunks; qwen3-embedding:4b; 2560D
memory       ok          3 facts; qwen3-embedding:4b; 2560D
metadata     ok          3
extraction   ok          3
```

No model was downloaded. The missing brain model intentionally blocked the
optional grounded `atelier ask` smoke test.

## 18. CLI changes

Existing commands remain intact. The canonical commands now include:

```text
atelier
atelier ingest PATH... [--force] [--dry-run] [--sync] [--reset]
atelier search QUERY [--source FILE] [--section-type TYPE] [--debug]
atelier paper PATH [--ingest]
atelier benchmark-retrieval
atelier memory-migrate
atelier doctor
```

The compact banner appears once only for the persistent session. Standalone
commands do not print it. The session forwards existing Typer commands instead
of duplicating command implementations and falls back to `python -m atelier.cli`
when the executable is not on `PATH`.

Retrieved, model-generated, and extracted document bodies are rendered with
Rich `Text`, preventing scientific strings such as `[/]`, `[1]`, Markdown, and
LaTeX-like notation from becoming terminal markup.

## 19. Tests added

New deterministic tests cover:

- manifest and incremental decisions;
- injected embedding counters;
- rename, modification, duplicate, sync, force, and dry-run behavior;
- conservative PDF cleanup and section types;
- strict paper metadata schemas;
- incompatible index rejection;
- reference intent, conceptual reference penalties, and diversity;
- memory backup migration and metadata preservation;
- Ollama JSON Schema forwarding.

## 20. Exact final test counts

Commands and results:

```text
.venv/bin/python -m pytest -q                 97 passed, 1 warning
atelier_agent/../.venv/bin/python -m pytest   83 collected and passed, 1 warning
python3 scripts/check_repo.py                 PASS
python3 scripts/validate_experiments.py       PASS
python3 -m compileall -q atelier_agent        PASS
git diff --check                              PASS
```

The root and `atelier_agent` suites must be run sequentially because both
exercise shared evaluation fixtures; a parallel run can race on those fixtures.
The warning is a third-party OpenTelemetry deprecation warning.

## 21. Real three-paper benchmark results

Command:

```text
ATELIER_NO_BANNER=1 atelier benchmark-retrieval
```

Measured result:

```text
5/5 expected-source retrieval hits
0 reference-dominated queries
qwen3-embedding:4b
2560 dimensions
```

The tested queries were SAA regret bounds, quantum CVaR tail-risk decision
quality, CVaR decision-gap estimation error, inventory-control literature, and
the broad query `quantum`. The literature query retained References; the broad
concept query returned substantive sections in its top three.

## 22. Exact commands used

```bash
python3 scripts/check_repo.py
python3 scripts/validate_experiments.py
.venv/bin/python -m pytest -q
cd atelier_agent && ../.venv/bin/python -m pytest -q
../.venv/bin/atelier ingest --dry-run data/corpus/papers
../.venv/bin/atelier ingest --force data/corpus/papers
../.venv/bin/atelier benchmark-retrieval
../.venv/bin/atelier paper data/corpus/papers/Data-Driven\ Newsvendor\ Problem.pdf
../.venv/bin/atelier memory-migrate
../.venv/bin/atelier doctor
../.venv/bin/atelier sources
```

## 23. Known limitations

- The three-paper benchmark is a small local regression suite, not a general
  information-retrieval benchmark.
- Native PDF extraction is preferred; scanned-PDF OCR and visual figure/table
  understanding remain deferred.
- The LFM worker is not trusted for difficult mathematical verification or
  novel scientific conclusions.
- `qwen3:14b` is configured as the brain but is not installed locally, so the
  grounded answer smoke test was not run.
- ArXiv/DOI sanitization is conservative validation, not external identifier
  verification.
- The section heuristic is deterministic and title-based; ambiguous headings
  resolve to `other`.

## 24. Explicitly deferred work

Deferred after this milestone: coding-specialist/Ornith integration, vision
models and OCR, Qwen3.8-27B, automatic model routing, LangGraph, Open WebUI,
cloud routing, LiteLLM, quantum/optimization domain tools, large repository
semantic indexing, fine-tuning, LoRA changes, and autonomous multi-agent
orchestration.

## 25. Freeze criteria

The local implementation satisfies the freeze criteria:

- tests pass;
- root checks pass;
- three PDFs are discoverable;
- the index is Qwen3-Embedding-4B / 2,560D;
- unchanged second ingest performs no extraction or embedding;
- rename preserves identity and does not re-embed;
- modification receives a new identity and removes stale chunks;
- incompatible dimensions produce an Atelier-level rebuild message;
- identity and characterization are separate and schema-validated;
- broad quantum retrieval is not reference-dominated;
- reference search remains valid;
- Rich-safe rendering is implemented;
- memory migration is backed up and count-verified;
- doctor reports model/index/memory state;
- documentation matches the implementation.

## 26. Final PASS/FAIL assessment

**PASS. Scientific Library v1.0 is locally freezeable.**

The only recorded non-green status is intentional model availability:
`qwen3:14b` and the optional `qwen3:4b` router are not installed. No model was
downloaded to obtain this result, and no GitHub push or merge was performed.
