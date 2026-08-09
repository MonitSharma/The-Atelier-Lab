"""Content-addressed index manifest for incremental local ingestion."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atelier.config import settings


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    current_path: str
    filename: str
    size_bytes: int
    mtime_ns: int
    chunk_count: int
    indexed_at: float
    updated_at: float
    doc_type: str
    metadata_schema_version: int


class IndexManifest:
    """Small SQLite catalog; Chroma remains the vector index."""

    def __init__(self, path: str | Path | None = None) -> None:
        settings.ensure_dirs()
        self.path = Path(path or settings.manifest_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    current_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    indexed_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    doc_type TEXT NOT NULL,
                    metadata_schema_version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS document_paths (
                    document_id TEXT NOT NULL,
                    path TEXT NOT NULL UNIQUE,
                    is_current INTEGER NOT NULL DEFAULT 0,
                    seen_at REAL NOT NULL,
                    PRIMARY KEY(document_id, path),
                    FOREIGN KEY(document_id) REFERENCES documents(document_id)
                );
                CREATE TABLE IF NOT EXISTS index_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_document_paths_path
                    ON document_paths(path);
                """
            )

    @staticmethod
    def _record(row: sqlite3.Row | None) -> DocumentRecord | None:
        if row is None:
            return None
        return DocumentRecord(**dict(row))

    def get(self, document_id: str) -> DocumentRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
        return self._record(row)

    def get_by_path(self, path: str | Path) -> DocumentRecord | None:
        normalized = str(Path(path).expanduser().resolve())
        with self._connect() as conn:
            row = conn.execute(
                """SELECT d.* FROM documents d JOIN document_paths p
                   ON p.document_id = d.document_id WHERE p.path = ?""",
                (normalized,),
            ).fetchone()
        return self._record(row)

    def all(self) -> list[DocumentRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM documents ORDER BY current_path").fetchall()
        return [self._record(row) for row in rows if row is not None]

    def paths_for(self, document_id: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT path FROM document_paths WHERE document_id = ? ORDER BY path",
                (document_id,),
            ).fetchall()
        return [str(row[0]) for row in rows]

    def upsert_document(
        self,
        *,
        document_id: str,
        path: str | Path,
        size_bytes: int,
        mtime_ns: int,
        chunk_count: int,
        doc_type: str,
        metadata_schema_version: int | None = None,
    ) -> None:
        normalized = str(Path(path).expanduser().resolve())
        now = time.time()
        schema = metadata_schema_version or settings.metadata_schema_version
        with self._connect() as conn:
            old = conn.execute(
                "SELECT indexed_at FROM documents WHERE document_id = ?", (document_id,)
            ).fetchone()
            indexed_at = float(old[0]) if old else now
            conn.execute(
                """INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(document_id) DO UPDATE SET
                   current_path=excluded.current_path, filename=excluded.filename,
                   size_bytes=excluded.size_bytes, mtime_ns=excluded.mtime_ns,
                   chunk_count=excluded.chunk_count, updated_at=excluded.updated_at,
                   doc_type=excluded.doc_type,
                   metadata_schema_version=excluded.metadata_schema_version""",
                (document_id, normalized, Path(normalized).name, size_bytes, mtime_ns,
                 chunk_count, indexed_at, now, doc_type, schema),
            )
            conn.execute(
                """INSERT INTO document_paths VALUES (?, ?, 1, ?)
                   ON CONFLICT(document_id, path) DO UPDATE SET
                   is_current=1, seen_at=excluded.seen_at""",
                (document_id, normalized, now),
            )
            conn.execute(
                "UPDATE document_paths SET is_current=0 WHERE document_id=? AND path<>?",
                (document_id, normalized),
            )

    def add_alias(self, document_id: str, path: str | Path) -> None:
        normalized = str(Path(path).expanduser().resolve())
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO document_paths VALUES (?, ?, 0, ?)
                   ON CONFLICT(document_id, path) DO UPDATE SET seen_at=excluded.seen_at""",
                (document_id, normalized, time.time()),
            )

    def remove(self, document_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM document_paths WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM documents WHERE document_id=?", (document_id,))

    def remove_path(self, path: str | Path) -> str | None:
        normalized = str(Path(path).expanduser().resolve())
        with self._connect() as conn:
            row = conn.execute(
                "SELECT document_id FROM document_paths WHERE path=?", (normalized,)
            ).fetchone()
            if row is None:
                return None
            document_id = str(row[0])
            conn.execute("DELETE FROM document_paths WHERE path=?", (normalized,))
            remaining = conn.execute(
                "SELECT path FROM document_paths WHERE document_id=? ORDER BY is_current DESC, path",
                (document_id,),
            ).fetchall()
            if not remaining:
                conn.execute("DELETE FROM documents WHERE document_id=?", (document_id,))
            else:
                current = str(remaining[0][0])
                conn.execute(
                    "UPDATE documents SET current_path=?, filename=?, updated_at=? WHERE document_id=?",
                    (current, Path(current).name, time.time(), document_id),
                )
        return document_id

    def set_state(self, **values: Any) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO index_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                [(key, str(value)) for key, value in values.items()],
            )

    def state(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key,value FROM index_state").fetchall()
        return {str(row[0]): str(row[1]) for row in rows}

    def reset(self) -> None:
        with self._connect() as conn:
            conn.executescript("DELETE FROM document_paths; DELETE FROM documents; DELETE FROM index_state;")
