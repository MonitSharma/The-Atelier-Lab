"""Safe, dry-run-first retention planning for persisted workflow runs."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def retention_candidates(
    storage_dir: Path,
    *,
    keep_successful: int = 20,
    failed_days: int = 30,
) -> list[dict[str, Any]]:
    """Return deletable run files without deleting anything."""
    if keep_successful < 0 or failed_days < 0:
        raise ValueError("retention limits cannot be negative")
    rows: list[dict[str, Any]] = []
    for path in storage_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            rows.append({
                "path": str(path),
                "run_id": payload.get("run_id", path.stem),
                "workflow": payload.get("workflow"),
                "status": payload.get("status"),
                "updated_at": payload.get("updated_at"),
                "mtime": path.stat().st_mtime,
            })
        except (OSError, json.JSONDecodeError, TypeError):
            continue
    rows.sort(key=lambda row: row["mtime"], reverse=True)
    protected = {
        id(row)
        for row in rows
        if row["status"] in {"completed", "partial"}
    }
    for row in rows[:keep_successful]:
        protected.add(id(row))
    cutoff = (datetime.now(UTC) - timedelta(days=failed_days)).timestamp()
    candidates: list[dict[str, Any]] = []
    for row in rows:
        if id(row) in protected or row["status"] in {"queued", "running", "waiting_approval"}:
            continue
        if row["status"] in {"failed", "cancelled"} and row["mtime"] < cutoff:
            candidates.append(row)
    return candidates


def apply_retention(candidates: list[dict[str, Any]]) -> list[str]:
    """Delete only the exact files returned by ``retention_candidates``."""
    removed: list[str] = []
    for row in candidates:
        path = Path(str(row["path"])).resolve()
        if path.parent != path.parent.resolve():  # defensive, keeps intent explicit
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        removed.append(str(path))
    return removed
