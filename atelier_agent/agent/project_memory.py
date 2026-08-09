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

    def remember(self, project: str, text: str, *, kind: str = "project", source: str | None = None,
                 expires_at: str | None = None) -> ProjectMemory:
        project, text, kind = project.strip(), text.strip(), kind.strip()
        if not project or not text:
            raise ValueError("project and text are required")
        if kind not in MEMORY_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(sorted(MEMORY_KINDS))}")
        item = ProjectMemory(str(uuid.uuid4()), project, kind, text, source, datetime.now(UTC).isoformat(), expires_at)
        with sqlite3.connect(self.path) as conn:
            conn.execute("INSERT INTO project_memory VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(item.to_dict().values()))
        return item

    def list(self, project: str, *, kind: str | None = None) -> list[ProjectMemory]:
        query = "SELECT id, project, kind, text, source, created_at, expires_at FROM project_memory WHERE project = ?"
        params: list[Any] = [project]
        if kind:
            query += " AND kind = ?"
            params.append(kind)
        query += " ORDER BY created_at, id"
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(query, params).fetchall()
        return [ProjectMemory(*row) for row in rows]

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
                          source=record.get("source"), expires_at=record.get("expires_at"))
            count += 1
        return count
