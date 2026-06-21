"""Local text search over the workspace (grep-like, no network).

A literal/regex search across workspace files. Kept deliberately local: the
project's locality constraint (PROJECT.md §1) rules out web search, so the
agent's "search" means searching *your* files. Semantic search over your notes
lives in the separate ``search_notes`` tool (RAG).
"""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool
from tools.files import _resolve_workspace_path

_SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
         ".ruff_cache", "data", "dist", "build"}
_TEXT_EXT = {".py", ".md", ".txt", ".toml", ".cfg", ".ini", ".json", ".yaml",
             ".yml", ".js", ".ts", ".sh", ".rst"}
_MAX_HITS = 100


def run_search(arguments: dict[str, Any]) -> dict[str, Any]:
    pattern = arguments.get("pattern")
    path = arguments.get("path", ".")
    if not isinstance(pattern, str) or not pattern:
        return {"status": "error", "error_type": "invalid_arguments",
                "message": "search requires a non-empty string 'pattern'."}
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return {"status": "error", "error_type": "bad_pattern", "message": str(exc)}
    try:
        root = _resolve_workspace_path(path if isinstance(path, str) else ".")
    except ValueError as exc:
        return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}

    hits: list[dict[str, Any]] = []
    files = [root] if root.is_file() else root.rglob("*")
    for p in sorted(files):
        if p.is_dir() or p.suffix not in _TEXT_EXT:
            continue
        if any(part in _SKIP for part in p.parts):
            continue
        try:
            for lineno, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if regex.search(line):
                    hits.append({"file": str(p), "line": lineno, "text": line.strip()[:200]})
                    if len(hits) >= _MAX_HITS:
                        return {"status": "success", "tool": "search", "truncated": True, "hits": hits}
        except OSError:
            continue

    return {"status": "success", "tool": "search", "truncated": False, "hits": hits}


SEARCH_TOOL = Tool(
    name="search",
    description=(
        "Search workspace files for a regular expression and return matching "
        "file:line:text. Use to locate code, symbols, or text across the repo."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Python regular expression."},
            "path": {"type": "string", "description": "Workspace path to search under (default '.')."},
        },
        "required": ["pattern"],
        "additionalProperties": False,
    },
    function=run_search,
)
