"""Explicit project-scoped memory v2, separate from semantic user memory."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atelier.config import settings

MEMORY_KINDS = frozenset({"durable_user_fact", "task_state", "source_note", "project", "artifact", "decision"})


@dataclass(frozen=True)
class ProjectMemory:
    id: str
    project: str
    kind: str
    text: str
    source: str | None
    created_at: str
    expires_at: str | None = None
    provenance: dict[str, Any] | None = None
    session_id: str | None = None
    task_id: str | None = None
    artifact_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectMemoryStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or settings.project_memory_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS project_memory (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, kind TEXT NOT NULL,
                text TEXT NOT NULL, source TEXT, created_at TEXT NOT NULL, expires_at TEXT
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_project_memory_project ON project_memory(project)")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(project_memory)")}
            for name, definition in (
                ("provenance", "TEXT"), ("session_id", "TEXT"),
                ("task_id", "TEXT"), ("artifact_id", "TEXT"),
            ):
                if name not in columns:
                    conn.execute(f"ALTER TABLE project_memory ADD COLUMN {name} {definition}")
            conn.execute("""CREATE TABLE IF NOT EXISTS project_entities (
                entity_id TEXT PRIMARY KEY, project TEXT NOT NULL, entity_type TEXT NOT NULL,
                status TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, expires_at TEXT
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_project_entities_project ON project_entities(project, entity_type)")
            conn.execute("""CREATE TABLE IF NOT EXISTS project_context (
                project TEXT PRIMARY KEY, session_id TEXT, updated_at TEXT NOT NULL
            )""")

    @staticmethod
    def _record(row: tuple[Any, ...]) -> ProjectMemory:
        return ProjectMemory(
            id=str(row[0]), project=str(row[1]), kind=str(row[2]), text=str(row[3]),
            source=row[4], created_at=str(row[5]), expires_at=row[6],
            provenance=json.loads(row[7]) if row[7] else None,
            session_id=row[8], task_id=row[9], artifact_id=row[10],
        )

    @staticmethod
    def _expired(expires_at: str | None, now: datetime | None = None) -> bool:
        if not expires_at:
            return False
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            return expiry <= (now or datetime.now(UTC))
        except ValueError:
            return False

    def remember(
        self,
        project: str,
        text: str,
        *,
        kind: str = "project",
        source: str | None = None,
        expires_at: str | None = None,
        provenance: dict[str, Any] | None = None,
        session_id: str | None = None,
        task_id: str | None = None,
        artifact_id: str | None = None,
    ) -> ProjectMemory:
        project, text, kind = project.strip(), text.strip(), kind.strip()
        if not project or not text:
            raise ValueError("project and text are required")
        if kind not in MEMORY_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(sorted(MEMORY_KINDS))}")
        item = ProjectMemory(str(uuid.uuid4()), project, kind, text, source, datetime.now(UTC).isoformat(), expires_at, provenance, session_id, task_id, artifact_id)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO project_memory (id, project, kind, text, source, created_at, expires_at, provenance, session_id, task_id, artifact_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item.id, item.project, item.kind, item.text, item.source, item.created_at, item.expires_at,
                 json.dumps(item.provenance, sort_keys=True) if item.provenance is not None else None,
                 item.session_id, item.task_id, item.artifact_id),
            )
        return item

    def list(self, project: str, *, kind: str | None = None, include_expired: bool = False) -> list[ProjectMemory]:
        query = "SELECT id, project, kind, text, source, created_at, expires_at, provenance, session_id, task_id, artifact_id FROM project_memory WHERE project = ?"
        params: list[Any] = [project]
        if kind:
            query += " AND kind = ?"
            params.append(kind)
        query += " ORDER BY created_at, id"
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(query, params).fetchall()
        items = [self._record(row) for row in rows]
        return items if include_expired else [item for item in items if not self._expired(item.expires_at)]

    def forget(self, memory_id: str, project: str) -> bool:
        with sqlite3.connect(self.path) as conn:
            result = conn.execute("DELETE FROM project_memory WHERE id = ? AND project = ?", (memory_id, project))
        return result.rowcount == 1

    def export(self, project: str, path: str | Path) -> Path:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps([m.to_dict() for m in self.list(project)], indent=2) + "\n", encoding="utf-8")
        return target

    def import_file(self, project: str, path: str | Path) -> int:
        records = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("memory export must contain a list")
        count = 0
        for record in records:
            if not isinstance(record, dict):
                continue
            self.remember(project, str(record["text"]), kind=str(record.get("kind", "project")),
                          source=record.get("source"), expires_at=record.get("expires_at"),
                          provenance=record.get("provenance"), session_id=record.get("session_id"),
                          task_id=record.get("task_id"), artifact_id=record.get("artifact_id"))
            count += 1
        return count

    def purge_expired(self, project: str | None = None) -> int:
        """Delete only records whose explicit expiry has passed."""
        candidates = self.list(project or "", include_expired=True) if project else self._all()
        expired = [item for item in candidates if self._expired(item.expires_at)]
        with sqlite3.connect(self.path) as conn:
            if expired:
                conn.executemany("DELETE FROM project_memory WHERE id = ?", [(item.id,) for item in expired])
        return len(expired)

    def _all(self) -> list[ProjectMemory]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT id, project, kind, text, source, created_at, expires_at, provenance, session_id, task_id, artifact_id FROM project_memory ORDER BY created_at, id").fetchall()
        return [self._record(row) for row in rows]

    def upsert_entity(
        self,
        project: str,
        entity_id: str,
        entity_type: str,
        data: dict[str, Any],
        *,
        status: str = "active",
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        if not project.strip() or not entity_id.strip() or not entity_type.strip():
            raise ValueError("project, entity_id, and entity_type are required")
        now = datetime.now(UTC).isoformat()
        record = {"entity_id": entity_id, "project": project, "entity_type": entity_type, "status": status,
                  "data": data, "created_at": now, "updated_at": now, "expires_at": expires_at}
        with sqlite3.connect(self.path) as conn:
            old = conn.execute("SELECT created_at FROM project_entities WHERE entity_id = ?", (entity_id,)).fetchone()
            record["created_at"] = old[0] if old else now
            conn.execute(
                """INSERT INTO project_entities(entity_id, project, entity_type, status, data, created_at, updated_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(entity_id) DO UPDATE SET project=excluded.project, entity_type=excluded.entity_type,
                   status=excluded.status, data=excluded.data, updated_at=excluded.updated_at, expires_at=excluded.expires_at""",
                (entity_id, project, entity_type, status, json.dumps(data, sort_keys=True, default=str), record["created_at"], now, expires_at),
            )
        return record

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT entity_id, project, entity_type, status, data, created_at, updated_at, expires_at FROM project_entities WHERE entity_id = ?", (entity_id,)).fetchone()
        if row is None or self._expired(row[7]):
            return None
        return {"entity_id": row[0], "project": row[1], "entity_type": row[2], "status": row[3],
                "data": json.loads(row[4]), "created_at": row[5], "updated_at": row[6], "expires_at": row[7]}

    def list_entities(self, project: str, *, entity_type: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT entity_id, project, entity_type, status, data, created_at, updated_at, expires_at FROM project_entities WHERE project = ?"
        params: list[Any] = [project]
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        query += " ORDER BY updated_at, entity_id"
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [item for row in rows if (item := self.get_entity(str(row[0]))) is not None]

    def set_active_context(self, project: str, session_id: str | None = None) -> dict[str, str | None]:
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO project_context(project, session_id, updated_at) VALUES (?, ?, ?) ON CONFLICT(project) DO UPDATE SET session_id=excluded.session_id, updated_at=excluded.updated_at", (project, session_id, datetime.now(UTC).isoformat()))
        return {"project": project, "session_id": session_id}

    def active_context(self, project: str) -> dict[str, str | None] | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT project, session_id FROM project_context WHERE project = ?", (project,)).fetchone()
        return {"project": row[0], "session_id": row[1]} if row else None
