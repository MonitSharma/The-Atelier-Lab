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

from pathlib import Path
from dotenv import load_dotenv

# Load .env file to populate environment variables like HF_TOKEN
load_dotenv()

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = parent of this `atelier/` package directory.
ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATELIER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Local model serving (Ollama) -------------------------------------
    ollama_url: str = "http://localhost:11434"
    #: Hard reasoning + build mode. Fits comfortably in 36 GB.
    brain_model: str = "qwen3:14b"
    #: Fast, cheap subtasks / routing.
    worker_model: str = "qwen3:4b"
    #: Optional heavy reasoner for the hardest steps (~17 GB resident).
    heavy_model: str = "gemma4:26b"
    temperature: float = 0.1
    #: Generous: a 14B local model on first load can be slow to first token.
    request_timeout: int = 600
    #: Truncate retrieved context fed to the model (characters).
    max_context_chars: int = 12_000

    # --- Embeddings / RAG --------------------------------------------------
    embed_model: str = "BAAI/bge-base-en-v1.5"
    #: bge-v1.5 retrieval works best with this instruction prepended to queries
    #: (passages are embedded bare). See the model card.
    query_instruction: str = "Represent this sentence for searching relevant passages: "
    #: "mps" uses the Apple-Silicon GPU; falls back to "cpu" automatically.
    embed_device: str = "mps"
    embed_batch_size: int = 32
    chunk_size: int = 1000  # characters
    chunk_overlap: int = 150  # characters
    retrieval_k: int = 6

    # --- Paths (all under the repo, all local) ----------------------------
    root: Path = ROOT
    data_dir: Path = ROOT / "data"
    corpus_dir: Path = ROOT / "data" / "corpus"
    vector_dir: Path = ROOT / "data" / "vectorstore"
    memory_dir: Path = ROOT / "data" / "memory"
    traces_dir: Path = ROOT / "data" / "traces"
    collection_name: str = "atelier"

    def ensure_dirs(self) -> None:
        """Create the runtime data directories if they don't exist."""
        for d in (self.data_dir, self.corpus_dir, self.vector_dir,
                  self.memory_dir, self.traces_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
