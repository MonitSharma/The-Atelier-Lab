"""Release and clean-install readiness checks."""

from __future__ import annotations

import ast
import platform
import sys
from pathlib import Path
from typing import Any

REQUIRED_FILES = ("pyproject.toml", "requirements.txt", "README.md", "atelier/cli.py")


def package_check(root: str | Path) -> dict[str, Any]:
    base = Path(root).expanduser().resolve()
    missing = [item for item in REQUIRED_FILES if not (base / item).exists()]
    syntax_errors = []
    python_files = list((base / "atelier").rglob("*.py")) if (base / "atelier").exists() else []
    for path in python_files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            syntax_errors.append({"file": str(path), "error": str(exc)})
    return {"valid": not missing and not syntax_errors, "root": str(base),
            "python": sys.version.split()[0], "platform": platform.platform(),
            "required_files": list(REQUIRED_FILES), "missing": missing,
            "syntax_errors": syntax_errors}
