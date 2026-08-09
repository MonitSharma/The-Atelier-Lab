"""Agent-facing wrappers around deterministic repository inspection."""

from __future__ import annotations

from typing import Any

from repo.inspector import RepositoryInspectionError, RepositoryInspector
from tools.base import Tool
from tools.files import _resolve_workspace_path


def _inspector(arguments: dict[str, Any]) -> RepositoryInspector:
    path = arguments.get("path", ".")
    if not isinstance(path, str):
        raise RepositoryInspectionError("Repository path must be a string.")
    return RepositoryInspector.for_path(_resolve_workspace_path(path, "read"))


def run_repo_inspect(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"status": "success", "tool": "repo_inspect", "profile": _inspector(arguments).inspect()}
    except (ValueError, OSError) as exc:
        return {"status": "error", "error_type": "repository_inspection_error", "message": str(exc)}


def run_repo_status(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        inspector = _inspector(arguments)
        return {
            "status": "success", "tool": "repo_status", "status_info": inspector.git_status(),
            "history": inspector.git_history(), "diff": inspector.git_diff(),
        }
    except (ValueError, OSError) as exc:
        return {"status": "error", "error_type": "repository_inspection_error", "message": str(exc)}


def run_repo_symbols(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"status": "success", "tool": "repo_symbols", "symbols": _inspector(arguments).symbols()}
    except (ValueError, OSError) as exc:
        return {"status": "error", "error_type": "repository_inspection_error", "message": str(exc)}


def run_repo_search(arguments: dict[str, Any]) -> dict[str, Any]:
    pattern = arguments.get("pattern")
    if not isinstance(pattern, str) or not pattern:
        return {"status": "error", "error_type": "invalid_arguments", "message": "pattern is required."}
    try:
        return {"status": "success", "tool": "repo_search", "hits": _inspector(arguments).search(pattern)}
    except (ValueError, OSError) as exc:
        return {"status": "error", "error_type": "repository_inspection_error", "message": str(exc)}


def run_repo_tests(arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        inspector = _inspector(arguments)
        return {"status": "success", "tool": "repo_tests", "tests": inspector.test_frameworks()}
    except (ValueError, OSError) as exc:
        return {"status": "error", "error_type": "repository_inspection_error", "message": str(exc)}


def _tool(name: str, description: str, function, properties: dict[str, Any], required: list[str] | None = None) -> Tool:
    return Tool(
        name=name,
        description=description,
        input_schema={
            "type": "object", "properties": properties,
            "required": required or [], "additionalProperties": False,
        },
        function=function,
    )


_PATH = {"path": {"type": "string", "description": "Approved workspace path to a repository."}}
REPO_INSPECT_TOOL = _tool("repo_inspect", "Inspect repository structure, Git, environments, tests, symbols, and file importance deterministically.", run_repo_inspect, _PATH)
REPO_STATUS_TOOL = _tool("repo_status", "Inspect Git branch, cleanliness, history, and diff for an approved repository.", run_repo_status, _PATH)
REPO_SYMBOLS_TOOL = _tool("repo_symbols", "List deterministic symbols and imports without executing repository source.", run_repo_symbols, _PATH)
REPO_SEARCH_TOOL = _tool("repo_search", "Search an approved repository with a deterministic regular expression.", run_repo_search, {**_PATH, "pattern": {"type": "string"}}, ["pattern"])
REPO_TESTS_TOOL = _tool("repo_tests", "Detect repository test frameworks and their likely commands.", run_repo_tests, _PATH)

