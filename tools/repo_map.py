"""Repo map: a compact, structured view of a codebase the agent can navigate.

Returns a file tree plus, for Python files, an outline of top-level classes and
functions (via the ``ast`` module — no execution). This gives the brain a cheap
mental model of a repo without reading every file into context.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from tools import files as file_tools
from tools.base import Tool
from tools.files import _resolve_workspace_path

_SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
         ".ruff_cache", "data", "dist", "build", ".mypy_cache"}
_MAX_FILES = 400


def _py_outline(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return []
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            names.append(f"class {node.name}(" + ", ".join(methods) + ")")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(f"def {node.name}()")
    return names


def run_repo_map(arguments: dict[str, Any]) -> dict[str, Any]:
    target = arguments.get("path", ".")
    if not isinstance(target, str):
        return {"status": "error", "error_type": "invalid_arguments",
                "message": "repo_map 'path' must be a string."}
    try:
        root = _resolve_workspace_path(target)
    except ValueError as exc:
        return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}
    if not root.exists():
        return {"status": "error", "error_type": "not_found", "message": f"No such path: {target}"}

    lines: list[str] = []
    count = 0
    for p in sorted(root.rglob("*")):
        if any(part in _SKIP for part in p.relative_to(root).parts):
            continue
        if p.is_dir():
            continue
        count += 1
        if count > _MAX_FILES:
            lines.append("... (truncated)")
            break
        rel = p.relative_to(file_tools.PROJECT_ROOT)
        lines.append(str(rel))
        if p.suffix == ".py":
            for sym in _py_outline(p):
                lines.append(f"    {sym}")

    return {
        "status": "success",
        "tool": "repo_map",
        "root": str(root),
        "file_count": count,
        "map": "\n".join(lines),
    }


REPO_MAP_TOOL = Tool(
    name="repo_map",
    description=(
        "Produce a structured map of a directory: the file tree plus an outline "
        "of top-level classes/functions for Python files. Use this FIRST to "
        "understand a codebase before reading or editing specific files."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace path to map (default '.')."},
        },
        "required": [],
        "additionalProperties": False,
    },
    function=run_repo_map,
)
