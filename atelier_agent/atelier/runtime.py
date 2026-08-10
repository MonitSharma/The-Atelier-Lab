"""Versioned user runtime-home layout and recoverable state migration."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RUNTIME_VERSION = 1


def default_home() -> Path:
    return Path(os.environ.get("ATELIER_HOME", Path.home() / "Atelier")).expanduser().resolve()


@dataclass(frozen=True)
class RuntimeLayout:
    root: Path
    version: int = RUNTIME_VERSION

    @property
    def library(self) -> Path:
        return self.root / "library"

    @property
    def databases(self) -> Path:
        return self.root / "databases"

    @property
    def workspaces(self) -> Path:
        return self.root / "workspaces"

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def manifest(self) -> Path:
        return self.root / "runtime-manifest.json"

    def directories(self) -> tuple[Path, ...]:
        return (self.library, self.databases, self.workspaces, self.config,
                self.cache, self.logs, self.backups)

    def to_dict(self) -> dict[str, Any]:
        return {"root": str(self.root), "version": self.version,
                "directories": {name: str(getattr(self, name)) for name in
                                ("library", "databases", "workspaces", "config", "cache", "logs", "backups")}}

    def initialize(self) -> "RuntimeLayout":
        self.root.mkdir(parents=True, exist_ok=True)
        for directory in self.directories():
            directory.mkdir(parents=True, exist_ok=True)
        self.manifest.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return self

    def validate(self) -> dict[str, Any]:
        errors = []
        if self.version != RUNTIME_VERSION:
            errors.append(f"unsupported runtime version: {self.version}")
        if not self.root.exists():
            errors.append("runtime home does not exist")
        for directory in self.directories():
            if not directory.is_dir():
                errors.append(f"missing directory: {directory}")
        if not self.manifest.exists():
            errors.append("runtime manifest is missing")
        return {"valid": not errors, "root": str(self.root), "version": self.version, "errors": errors}


def migration_plan(source: str | Path, destination: str | Path) -> dict[str, Any]:
    source_path, destination_path = Path(source).expanduser().resolve(), Path(destination).expanduser().resolve()
    files = []
    if source_path.exists():
        for path in sorted(item for item in source_path.rglob("*") if item.is_file()):
            relative = path.relative_to(source_path)
            files.append({"source": str(path), "destination": str(destination_path / relative), "bytes": path.stat().st_size})
    return {"source": str(source_path), "destination": str(destination_path), "files": files,
            "file_count": len(files), "bytes": sum(item["bytes"] for item in files)}


def migrate_state(source: str | Path, destination: str | Path) -> dict[str, Any]:
    plan = migration_plan(source, destination)
    destination_path = Path(plan["destination"])
    destination_path.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in plan["files"]:
        target = Path(item["destination"])
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"migration destination already exists: {target}")
        shutil.copy2(item["source"], target)
        copied.append(str(target))
    record = destination_path / "migration-record.json"
    record.write_text(json.dumps({"migrated_at": datetime.now(UTC).isoformat(), "source": plan["source"], "copied": copied}, indent=2) + "\n", encoding="utf-8")
    return {**plan, "copied": len(copied), "record": str(record)}


def legacy_migration_plan(source: str | Path, layout: RuntimeLayout) -> dict[str, Any]:
    """Map development-era ``data/`` paths into the active runtime layout."""
    source_path = Path(source).expanduser().resolve()
    mapping = {
        "corpus": layout.library / "corpus",
        "paper_metadata": layout.library / "paper_metadata",
        "extracted": layout.library / "extracted",
        "visual_cache": layout.cache / "visual",
        "vectorstore": layout.databases / "vectorstore",
        "memory": layout.databases / "memory",
        "memory_backups": layout.backups / "memory",
        "traces": layout.logs / "traces",
        "audit": layout.logs / "audit",
        "index_manifest.sqlite3": layout.databases / "index_manifest.sqlite3",
        "memory_manifest.sqlite3": layout.databases / "memory_manifest.sqlite3",
        "project_memory.sqlite3": layout.databases / "project_memory.sqlite3",
        "workspaces.json": layout.workspaces / "registry.json",
    }
    files: list[dict[str, Any]] = []
    for relative, destination in mapping.items():
        source_item = source_path / relative
        if source_item.is_dir():
            for path in sorted(item for item in source_item.rglob("*") if item.is_file()):
                files.append({"source": str(path), "destination": str(destination / path.relative_to(source_item)), "bytes": path.stat().st_size})
        elif source_item.is_file():
            files.append({"source": str(source_item), "destination": str(destination), "bytes": source_item.stat().st_size})
    return {"source": str(source_path), "destination": str(layout.root), "files": files,
            "file_count": len(files), "bytes": sum(item["bytes"] for item in files),
            "mapping": {key: str(value) for key, value in mapping.items()}}


def migrate_legacy_state(source: str | Path, layout: RuntimeLayout) -> dict[str, Any]:
    layout.initialize()
    plan = legacy_migration_plan(source, layout)
    copied: list[str] = []
    for item in plan["files"]:
        target = Path(item["destination"])
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f"migration destination already exists: {target}")
        shutil.copy2(item["source"], target)
        copied.append(str(target))
    record = layout.backups / f"legacy-migration-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    record.write_text(json.dumps({"migrated_at": datetime.now(UTC).isoformat(), "source": plan["source"], "copied": copied}, indent=2) + "\n", encoding="utf-8")
    return {**plan, "copied": len(copied), "record": str(record)}


def rollback_migration(record_path: str | Path) -> dict[str, Any]:
    record = Path(record_path).expanduser().resolve()
    payload = json.loads(record.read_text(encoding="utf-8"))
    removed = []
    for raw_path in payload.get("copied", []):
        path = Path(raw_path)
        if path.is_file():
            path.unlink()
            removed.append(str(path))
    return {"removed": removed, "record": str(record), "source_preserved": payload.get("source")}


def runtime_layout(home: str | Path | None = None) -> RuntimeLayout:
    return RuntimeLayout(Path(home).expanduser().resolve() if home else default_home())
