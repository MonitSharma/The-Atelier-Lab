# Current Atelier Architecture

Status: **post-Scientific Library v1.0; core-consolidation work in progress**

## Shipped baseline

- CLI, persistent session, and MCP server share one application/tool registry.
- Local reasoning uses Ollama; the installed heavy fallback is `gemma4:26b`.
- The installed worker is LFM2.5-2.6B Q6_K.
- Retrieval uses `qwen3-embedding:4b` at 2,560 dimensions.
- ChromaDB stores vectors; SQLite stores document and compatibility manifests.
- PDF extraction is content-addressed, cached, and section-aware.
- Hybrid retrieval combines dense search, BM25, RRF, section adjustment, and
  deterministic diversity.
- Semantic memory has backup-backed migration and a separate collection.
- Root and agent dependencies are declared; Linux CI runs the full suite.
- `master` is protected and requires the `Python 3.11` Test workflow.

## Deliberate placeholders

`qwen3:14b` remains the default brain configuration and `qwen3:4b` remains the
router configuration, but neither is installed. These are benchmark decisions,
not setup failures. The project will choose future coding, routing, and vision
models through frozen evaluations rather than by accumulating downloads.

## Not shipped yet

- multi-workspace permissions and capability policy;
- deterministic repository intelligence at repository scale;
- a dedicated `coder` role and coding-model benchmark;
- plan/edit/verify transactions and rollback;
- domain-aware routing and model lifecycle management;
- multimodal documents, general-file adapters, network research tools;
- quantum/optimization tool families;
- workflow state, project-scoped memory, hardened security boundary;
- backend API, external runtime home, web/Finder interfaces, and handoffs.

The dependency-ordered roadmap for these capabilities is maintained in
[`ATELIER_WORKBENCH_PLAN.md`](ATELIER_WORKBENCH_PLAN.md).
