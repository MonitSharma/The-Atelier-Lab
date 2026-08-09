"""Trust-boundary checks, secret redaction, and audit events for tool calls."""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atelier.config import settings

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|access[_-]?token|auth[_-]?token|password|secret)\s*[:=]\s*[\"']?([A-Za-z0-9_./+=:-]{8,})"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_./+=:-]{8,}"),
)
_SHELL_OPERATORS = re.compile(r"(?:;|\|\||&&|[|<>`$])")
_DESTRUCTIVE_EXECUTABLES = frozenset({"rm", "rmdir", "unlink", "shred", "mkfs", "dd", "shutdown", "reboot", "killall"})
_ALLOWED_EXECUTABLES = frozenset({
    "cat", "find", "git", "head", "ls", "pwd", "pytest", "python", "python3",
    "rg", "ruff", "sed", "tail", "uv", "wc",
})


def redact_secrets(value: str) -> tuple[str, bool]:
    redacted = value
    changed = False
    for pattern in _SECRET_PATTERNS:
        replacement = r"\1=[REDACTED]" if "bearer" not in pattern.pattern.lower() else "Bearer [REDACTED]"
        redacted, count = pattern.subn(replacement, redacted)
        changed = changed or count > 0
    return redacted, changed


def protect_tool_output(value: Any) -> tuple[Any, bool]:
    """Redact secret-looking strings and preserve an untrusted-output marker."""
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        changed = False
        protected = {}
        for key, item in value.items():
            protected_item, item_changed = protect_tool_output(item)
            protected[key] = protected_item
            changed = changed or item_changed
        return protected, changed
    if isinstance(value, list):
        protected = []
        changed = False
        for item in value:
            protected_item, item_changed = protect_tool_output(item)
            protected.append(protected_item)
            changed = changed or item_changed
        return protected, changed
    return value, False


def validate_shell_command(command: str) -> tuple[bool, str]:
    if _SHELL_OPERATORS.search(command):
        return False, "shell operators and redirections are blocked; use one command per tool call"
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return False, f"invalid shell syntax: {exc}"
    if not tokens:
        return False, "empty shell command"
    executable = Path(tokens[0]).name
    if executable in _DESTRUCTIVE_EXECUTABLES:
        return False, "destructive commands require an explicit human-approved operation"
    if executable not in _ALLOWED_EXECUTABLES:
        return False, f"executable '{executable}' is not on the Atelier allowlist"
    if executable == "git" and len(tokens) > 1 and tokens[1] in {"clean", "reset", "checkout", "restore"}:
        return False, "destructive Git operations require an explicit human-approved operation"
    return True, "allowed"


@dataclass
class SecurityBoundary:
    """Apply preflight checks and append minimal audit events."""

    audit_path: Path | None = None

    def _path(self) -> Path:
        path = self.audit_path or settings.audit_log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def audit(self, *, tool: str, status: str, error_type: str | None = None) -> None:
        event = {
            "timestamp": datetime.now(UTC).isoformat(), "tool": tool,
            "status": status, "error_type": error_type,
        }
        with self._path().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def preflight(self, tool: str, arguments: dict[str, Any]) -> tuple[bool, str | None]:
        if tool == "shell":
            command = arguments.get("command")
            if not isinstance(command, str):
                return False, "shell requires a command"
            return validate_shell_command(command)
        return True, None

    def result(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        protected, changed = protect_tool_output(payload)
        assert isinstance(protected, dict)
        protected["_security"] = {"untrusted_tool_output": True, "secrets_redacted": changed}
        return protected
