"""Release and clean-install readiness checks."""

from __future__ import annotations

import ast
import platform
import sys
import zipfile
from pathlib import Path
from typing import Any

from atelier.runtime import runtime_layout

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


def export_runtime(home: str | Path, archive: str | Path) -> dict[str, Any]:
    """Create a portable ZIP backup of an initialized external runtime home."""
    source = Path(home).expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"Runtime home does not exist: {source}")
    target = Path(archive).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.resolve() != target:
                bundle.write(path, path.relative_to(source).as_posix())
                count += 1
    return {"status": "success", "archive": str(target), "files": count, "bytes": target.stat().st_size}


def restore_runtime(archive: str | Path, home: str | Path, *, overwrite: bool = False) -> dict[str, Any]:
    """Restore a ZIP backup after validating every member stays in the target home."""
    source = Path(archive).expanduser().resolve()
    target = runtime_layout(home).root
    if not source.is_file():
        raise ValueError(f"Runtime archive does not exist: {source}")
    target.mkdir(parents=True, exist_ok=True)
    restored: list[str] = []
    with zipfile.ZipFile(source) as bundle:
        members = [item for item in bundle.infolist() if not item.is_dir()]
        for member in members:
            destination = (target / member.filename).resolve()
            try:
                destination.relative_to(target.resolve())
            except ValueError as exc:
                raise ValueError(f"Archive path escapes runtime home: {member.filename}") from exc
            if destination.exists() and not overwrite:
                raise FileExistsError(f"restore destination already exists: {destination}")
        for member in members:
            destination = (target / member.filename).resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(bundle.read(member))
            restored.append(str(destination))
    return {"status": "success", "home": str(target), "restored": len(restored), "archive": str(source)}
