"""Cheap repository invariants; no network or optional ML dependencies."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["README.md", "ROADMAP.md", "LICENSE", "Makefile", "pyproject.toml", "docs/START_HERE.md", "experiments/registry.yaml"]


def registry_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in (ROOT / "experiments/registry.yaml").read_text().splitlines():
        if line.startswith("  - id:"):
            if current:
                entries.append(current)
            current = {"id": line.split(":", 1)[1].strip()}
        elif current and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key] = value.strip().strip('"')
    if current:
        entries.append(current)
    return entries


def main() -> int:
    errors: list[str] = [f"missing required file: {p}" for p in REQUIRED if not (ROOT / p).exists()]
    text = "\n".join(p.read_text(errors="ignore") for p in ROOT.rglob("*.md"))
    if "file:///Users/" in text:
        errors.append("absolute file:///Users link remains")
    if re.search(r"(?<![\w/])/Users/[A-Za-z0-9_.-]+", text):
        errors.append("absolute /Users path remains in markdown")
    entries = registry_entries()
    ids = [e.get("id", "") for e in entries]
    if len(ids) != len(set(ids)):
        errors.append("experiment IDs are not unique")
    for entry in entries:
        location = entry.get("location", "")
        if location and not (ROOT / location).exists():
            errors.append(f"registered location missing: {location}")
    if errors:
        print("\n".join(f"FAIL: {e}" for e in errors))
        return 1
    print(f"OK: {len(entries)} experiments registered; required files and path checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
