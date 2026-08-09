"""Central configuration for Atelier.

Everything tunable lives here, overridable via environment variables (prefix
``ATELIER_``) or a local ``.env`` file. Nothing here reaches the network except
the local Ollama endpoint and a one-time embedding-model download from Hugging
Face. No keys, no paid services — that is a hard constraint (PROJECT.md §1).

Example overrides::

    export ATELIER_BRAIN_MODEL=gemma4:26b
    export ATELIER_RETRIEVAL_K=8
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Load .env file to populate environment variables like HF_TOKEN
load_dotenv()

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = parent of this `atelier/` package directory.
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOME = Path(os.environ.get("ATELIER_HOME", Path.home() / "Atelier")).expanduser().resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATELIER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Local model serving (Ollama) -------------------------------------
    ollama_url: str = "http://localhost:11434"
    model_provider: str = "ollama"
    mlx_model_path: str | None = None
    #: Hard reasoning + build mode. Fits comfortably in 36 GB.
    brain_model: str = "qwen3:14b"
    #: Coding specialist selected by the Step 07 frozen benchmark.
    coder_model: str = "qwen3:8b"
    #: Fast, cheap subtasks / routing.
    worker_model: str = "hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q6_K"
    #: Optional heavy reasoner for the hardest steps (~17 GB resident).
    heavy_model: str = "gemma4:26b"
    #: Generic future expert slot; no unreleased model is assumed.
    expert_model: str = ""
    router_model: str = "qwen3:4b"
    temperature: float = 0.1
    #: Generous: a 14B local model on first load can be slow to first token.
    request_timeout: int = 600
    #: Truncate retrieved context fed to the model (characters).
    max_context_chars: int = 12_000

    # --- Embeddings / RAG --------------------------------------------------
    embed_model: str = "qwen3-embedding:4b"
    embed_dimension: int = 2560
    #: Qwen3 retrieval instruction. It is applied to queries only; passages
    #: remain plain text so the two embedding spaces stay compatible.
    query_instruction: str = (
        "Retrieve passages that are most relevant to the user's scientific "
        "research query. Prefer direct technical relevance over broad topical "
        "similarity. The library primarily contains artificial intelligence, "
        "quantum computing, optimization, operations research, mathematics, "
        "and scientific computing material."
    )
    #: Retained for compatibility with older configuration; Ollama performs
    #: inference locally and chooses the Apple-Silicon GPU automatically.
    embed_device: str = "mps"
    embed_batch_size: int = 32
    chunk_size: int = 1000  # characters
    chunk_overlap: int = 150  # characters
    paper_chunk_size: int = 1800
    paper_chunk_overlap: int = 250
    retrieval_k: int = 6

    # --- Hybrid retrieval + reranking -------------------------------------
    #: Fuse dense (vector) + lexical (BM25) results via Reciprocal Rank Fusion.
    use_hybrid: bool = True
    #: How many candidates each arm contributes before fusion/reranking.
    hybrid_candidates: int = 20
    #: RRF constant; larger = flatter weighting across ranks.
    rrf_k: int = 60
    #: Opt-in cross-encoder reranker (downloads ~80MB on first use). Off by
    #: default so retrieval stays dependency-light; turn on for best quality.
    rerank: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Paths (user state is external to the source checkout) ------------
    root: Path = ROOT
    home_dir: Path = DEFAULT_HOME
    legacy_data_dir: Path = ROOT / "data"
    data_dir: Path = DEFAULT_HOME
    corpus_dir: Path = DEFAULT_HOME / "library" / "corpus"
    vector_dir: Path = DEFAULT_HOME / "databases" / "vectorstore"
    memory_dir: Path = DEFAULT_HOME / "databases" / "memory"
    traces_dir: Path = DEFAULT_HOME / "logs" / "traces"
    collection_name: str = "atelier"
    paper_metadata_dir: Path = DEFAULT_HOME / "library" / "paper_metadata"
    extracted_dir: Path = DEFAULT_HOME / "library" / "extracted"
    visual_cache_dir: Path = DEFAULT_HOME / "cache" / "visual"
    research_cache_dir: Path = DEFAULT_HOME / "cache" / "research"
    manifest_path: Path = DEFAULT_HOME / "databases" / "index_manifest.sqlite3"
    memory_manifest_path: Path = DEFAULT_HOME / "databases" / "memory_manifest.sqlite3"
    memory_backup_dir: Path = DEFAULT_HOME / "backups" / "memory"
    project_memory_path: Path = DEFAULT_HOME / "databases" / "project_memory.sqlite3"
    audit_log_path: Path = DEFAULT_HOME / "logs" / "tool_calls.jsonl"
    workspace_registry_path: Path = DEFAULT_HOME / "workspaces" / "registry.json"
    metadata_schema_version: int = 2
    index_schema_version: int = 1
    chunk_schema_version: int = 2

    def model_post_init(self, __context: Any) -> None:
        """Derive default paths from ``ATELIER_HOME`` when it is overridden."""
        home = Path(self.home_dir).expanduser().resolve()
        defaults = {
            "data_dir": home,
            "corpus_dir": home / "library" / "corpus",
            "vector_dir": home / "databases" / "vectorstore",
            "memory_dir": home / "databases" / "memory",
            "traces_dir": home / "logs" / "traces",
            "paper_metadata_dir": home / "library" / "paper_metadata",
            "extracted_dir": home / "library" / "extracted",
            "visual_cache_dir": home / "cache" / "visual",
            "research_cache_dir": home / "cache" / "research",
            "manifest_path": home / "databases" / "index_manifest.sqlite3",
            "memory_manifest_path": home / "databases" / "memory_manifest.sqlite3",
            "memory_backup_dir": home / "backups" / "memory",
            "project_memory_path": home / "databases" / "project_memory.sqlite3",
            "audit_log_path": home / "logs" / "tool_calls.jsonl",
            "workspace_registry_path": home / "workspaces" / "registry.json",
        }
        for name, value in defaults.items():
            if name not in self.model_fields_set:
                setattr(self, name, value)

    def ensure_dirs(self) -> None:
        """Create the runtime data directories if they don't exist."""
        for d in (self.home_dir, self.data_dir, self.corpus_dir, self.vector_dir,
                  self.memory_dir, self.traces_dir, self.paper_metadata_dir,
                  self.extracted_dir, self.visual_cache_dir, self.research_cache_dir,
                  self.memory_backup_dir,
                  self.audit_log_path.parent, self.workspace_registry_path.parent):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
