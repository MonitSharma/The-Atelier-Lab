"""Deterministic, model-free repository characterization.

The inspector intentionally reports structure before semantics. It never sends
source files to a model and does not index every file into the scientific RAG
store. Its output is JSON-serializable so the CLI, coding workflow, and future
service layer can share one representation.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RepositoryInspectionError(ValueError):
    """Raised when a repository cannot be inspected safely."""


_SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", ".tox", "dist", "build", "target", ".next",
    ".idea", ".vscode", "data", "site-packages",
}
_LANGUAGES = {
    ".py": "Python", ".pyi": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".rs": "Rust", ".cpp": "C++",
    ".cc": "C++", ".cxx": "C++", ".h": "C/C++", ".hpp": "C++", ".c": "C",
    ".go": "Go", ".java": "Java", ".rb": "Ruby", ".swift": "Swift",
    ".md": "Markdown", ".json": "JSON", ".toml": "TOML", ".yaml": "YAML",
    ".yml": "YAML", ".sh": "Shell", ".sql": "SQL",
}
_PACKAGE_MARKERS = {
    "pyproject.toml": "Python / pyproject",
    "setup.py": "Python / setuptools",
    "setup.cfg": "Python / setuptools",
    "requirements.txt": "Python / pip",
    "requirements-dev.txt": "Python / pip",
    "uv.lock": "uv",
    "poetry.lock": "Poetry",
    "Pipfile": "Pipenv",
    "package.json": "Node / npm",
    "package-lock.json": "npm lockfile",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "Yarn",
    "Cargo.toml": "Rust / Cargo",
    "Cargo.lock": "Cargo lockfile",
    "CMakeLists.txt": "CMake",
    "Makefile": "Make",
    "go.mod": "Go modules",
    "Gemfile": "Ruby / Bundler",
}
_TEST_FILE_RE = re.compile(r"(^test_.*|.*_test|.*\.test|.*\.spec)(\.[^.]+)?$")


@dataclass(frozen=True)
class RepositoryInspector:
    root: Path
    max_files: int = 5000

    def __post_init__(self) -> None:
        root = self.root.expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise RepositoryInspectionError(f"Repository path must be an existing directory: {self.root}")
        object.__setattr__(self, "root", root)

    @classmethod
    def for_path(cls, path: str | Path, max_files: int = 5000) -> RepositoryInspector:
        path = Path(path).expanduser().resolve()
        if path.is_file():
            path = path.parent
        return cls(path, max_files=max_files)

    def _git_root(self) -> Path | None:
        result = self._git(["rev-parse", "--show-toplevel"])
        if result.returncode != 0:
            return None
        candidate = Path(result.stdout.strip()).resolve()
        return candidate if candidate.exists() else None

    def _git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", *args], cwd=self.root, capture_output=True, text=True,
                timeout=10, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return subprocess.CompletedProcess(["git", *args], 1, "", "git unavailable")

    def _files(self) -> tuple[list[Path], bool]:
        files: list[Path] = []
        truncated = False
        for current, dirs, names in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(name for name in dirs if name not in _SKIP_DIRS and not name.startswith("."))
            for name in sorted(names):
                path = Path(current) / name
                if path.is_symlink():
                    continue
                files.append(path)
                if len(files) >= self.max_files:
                    truncated = True
                    return files, truncated
        return files, truncated

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def git_status(self) -> dict[str, Any]:
        root = self._git_root()
        if root is None:
            return {"is_git": False, "root": None, "branch": None, "clean": None, "entries": []}
        branch = self._git(["branch", "--show-current"]).stdout.strip() or "HEAD"
        status = self._git(["status", "--porcelain=v1"]).stdout.splitlines()
        entries = [{"code": line[:2], "path": line[3:]} for line in status if len(line) >= 3]
        return {
            "is_git": True,
            "root": str(root),
            "branch": branch,
            "commit": self._git(["rev-parse", "HEAD"]).stdout.strip(),
            "clean": not entries,
            "entries": entries,
        }

    def git_history(self, limit: int = 10) -> list[dict[str, str]]:
        if self._git_root() is None:
            return []
        output = self._git(["log", f"-{max(1, min(limit, 50))}", "--pretty=%h%x09%ad%x09%s", "--date=short"]).stdout
        rows: list[dict[str, str]] = []
        for line in output.splitlines():
            short, date, subject = (line.split("\t", 2) + ["", "", ""])[:3]
            rows.append({"commit": short, "date": date, "subject": subject})
        return rows

    def git_diff(self) -> dict[str, Any]:
        if self._git_root() is None:
            return {"stat": "", "files": []}
        names = self._git(["diff", "--name-status"]).stdout.splitlines()
        return {
            "stat": self._git(["diff", "--stat"]).stdout.strip(),
            "files": [{"status": row[:1], "path": row[1:].strip()} for row in names if row],
        }

    def languages(self, files: list[Path] | None = None) -> dict[str, int]:
        files = files if files is not None else self._files()[0]
        counts = Counter(_LANGUAGES.get(path.suffix.lower(), "Other") for path in files)
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def package_managers(self, files: list[Path] | None = None) -> list[dict[str, str]]:
        files = files if files is not None else self._files()[0]
        names = {path.name for path in files if path.parent == self.root}
        return [{"file": name, "manager": manager} for name, manager in _PACKAGE_MARKERS.items() if name in names]

    def environments(self, files: list[Path] | None = None) -> list[dict[str, Any]]:
        files = files if files is not None else self._files()[0]
        names = {path.name for path in files if path.parent == self.root}
        relative_dirs = {self._rel(path).split("/", 1)[0] for path in files}
        environments: list[dict[str, Any]] = []
        if any(name in names for name in {"pyproject.toml", "setup.py", "requirements.txt", "setup.cfg"}):
            environments.append({"language": "Python", "virtualenv": ".venv" if (self.root / ".venv").exists() else None})
        if "package.json" in names:
            environments.append({"language": "JavaScript/TypeScript", "node_modules_present": "node_modules" in relative_dirs})
        if "Cargo.toml" in names:
            environments.append({"language": "Rust", "target_present": (self.root / "target").exists()})
        if "CMakeLists.txt" in names or "Makefile" in names:
            environments.append({"language": "C/C++", "build_system": "CMake" if "CMakeLists.txt" in names else "Make"})
        return environments

    def test_frameworks(self, files: list[Path] | None = None) -> list[dict[str, Any]]:
        files = files if files is not None else self._files()[0]
        rels = [self._rel(path) for path in files]
        names = {path.name for path in files if path.parent == self.root}
        frameworks: list[dict[str, Any]] = []
        python_tests = [rel for rel in rels if Path(rel).suffix == ".py" and _TEST_FILE_RE.match(Path(rel).stem)]
        if python_tests or "pytest.ini" in names or "tox.ini" in names:
            frameworks.append({"framework": "pytest", "tests": python_tests[:100], "command": "python -m pytest -q"})
        if any(Path(rel).suffix in {".js", ".jsx", ".ts", ".tsx"} and _TEST_FILE_RE.match(Path(rel).stem) for rel in rels):
            frameworks.append({"framework": "JavaScript test runner", "tests": [rel for rel in rels if ".test." in rel or ".spec." in rel][:100]})
        if "Cargo.toml" in names:
            frameworks.append({"framework": "cargo test", "command": "cargo test"})
        if "CMakeLists.txt" in names and any("test" in rel.lower() for rel in rels):
            frameworks.append({"framework": "CTest", "command": "ctest --test-dir build"})
        return frameworks

    def entry_points(self, files: list[Path] | None = None) -> list[dict[str, str]]:
        files = files if files is not None else self._files()[0]
        names = {path.name for path in files if path.parent == self.root}
        entries: list[dict[str, str]] = []
        pyproject = self.root / "pyproject.toml"
        if pyproject.exists():
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                for name, target in data.get("project", {}).get("scripts", {}).items():
                    entries.append({"kind": "python-script", "name": str(name), "target": str(target)})
            except (OSError, tomllib.TOMLDecodeError):
                pass
        if "package.json" in names:
            try:
                package = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
                if package.get("main"):
                    entries.append({"kind": "node-main", "name": "main", "target": str(package["main"])})
                for name, target in package.get("scripts", {}).items():
                    entries.append({"kind": "node-script", "name": str(name), "target": str(target)})
            except (OSError, json.JSONDecodeError):
                pass
        if "Cargo.toml" in names:
            try:
                data = tomllib.loads((self.root / "Cargo.toml").read_text(encoding="utf-8"))
                for binary in data.get("bin", []):
                    if isinstance(binary, dict):
                        entries.append({"kind": "cargo-bin", "name": str(binary.get("name", "")), "target": str(binary.get("path", ""))})
            except (OSError, tomllib.TOMLDecodeError):
                pass
        for name in ("__main__.py", "main.py", "app.py"):
            if name in names:
                entries.append({"kind": "python-file", "name": name, "target": name})
        return entries

    def symbols(self, files: list[Path] | None = None) -> list[dict[str, Any]]:
        files = files if files is not None else self._files()[0]
        rows: list[dict[str, Any]] = []
        for path in files:
            language = _LANGUAGES.get(path.suffix.lower())
            if language not in {"Python", "JavaScript", "TypeScript", "Rust", "C++", "C/C++", "C"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            names: list[dict[str, Any]] = []
            imports: list[str] = []
            if language == "Python":
                try:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            kind = "class" if isinstance(node, ast.ClassDef) else "function"
                            names.append({"name": node.name, "kind": kind, "line": node.lineno})
                        elif isinstance(node, ast.Import):
                            imports.extend(alias.name for alias in node.names)
                        elif isinstance(node, ast.ImportFrom):
                            imports.append("." * node.level + (node.module or ""))
                except SyntaxError:
                    pass
            else:
                patterns = {
                    "Rust": r"\b(?:fn|struct|enum|trait|mod)\s+([A-Za-z_][A-Za-z0-9_]*)",
                    "C++": r"\b(?:class|struct|namespace)\s+([A-Za-z_][A-Za-z0-9_]*)",
                    "C/C++": r"\b(?:class|struct|namespace)\s+([A-Za-z_][A-Za-z0-9_]*)",
                    "C": r"\b(?:struct)\s+([A-Za-z_][A-Za-z0-9_]*)",
                    "JavaScript": r"\b(?:function|class)\s+([A-Za-z_$][A-Za-z0-9_$]*)",
                    "TypeScript": r"\b(?:function|class|interface|type)\s+([A-Za-z_$][A-Za-z0-9_$]*)",
                }
                pattern = patterns.get(language, "")
                for match in re.finditer(pattern, text):
                    names.append({"name": match.group(1), "kind": "symbol", "line": text.count("\n", 0, match.start()) + 1})
                imports.extend(re.findall(r"^\s*(?:import|use|#include)\s+([^;\n]+)", text, re.MULTILINE))
            if names or imports:
                rows.append({"file": self._rel(path), "language": language, "symbols": names, "imports": sorted(set(imports))})
        return rows

    def test_relationships(self, files: list[Path] | None = None) -> list[dict[str, Any]]:
        files = files if files is not None else self._files()[0]
        source_by_stem: defaultdict[str, list[str]] = defaultdict(list)
        tests: list[Path] = []
        for path in files:
            stem = path.stem
            if path.suffix == ".py" and (stem.startswith("test_") or stem.endswith("_test")):
                tests.append(path)
            elif path.suffix in {".js", ".jsx", ".ts", ".tsx"} and (".test" in stem or ".spec" in stem):
                tests.append(path)
            else:
                source_by_stem[stem].append(self._rel(path))
        relationships: list[dict[str, Any]] = []
        for test in tests:
            candidates: set[str] = set()
            stem = test.stem.removeprefix("test_").removesuffix("_test")
            stem = stem.replace(".test", "").replace(".spec", "")
            candidates.update(source_by_stem.get(stem, []))
            try:
                text = test.read_text(encoding="utf-8", errors="replace")
                for source_stem, paths in source_by_stem.items():
                    if re.search(rf"\b{re.escape(source_stem)}\b", text):
                        candidates.update(paths)
            except OSError:
                pass
            relationships.append({"test": self._rel(test), "sources": sorted(candidates)})
        return relationships

    def important_files(self, files: list[Path] | None = None, relationships: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        files = files if files is not None else self._files()[0]
        relationships = relationships if relationships is not None else self.test_relationships(files)
        scores: Counter[str] = Counter()
        reasons: defaultdict[str, list[str]] = defaultdict(list)
        marker_names = set(_PACKAGE_MARKERS)
        for path in files:
            rel = self._rel(path)
            if path.name in marker_names:
                scores[rel] += 5
                reasons[rel].append("package/build marker")
            if path.name.lower().startswith(("readme", "project")):
                scores[rel] += 4
                reasons[rel].append("documentation entry point")
            if path.name in {"main.py", "app.py", "__main__.py", "index.js", "lib.rs", "main.rs"}:
                scores[rel] += 3
                reasons[rel].append("likely entry point")
            if "tests" in path.parts or path.name.startswith("test_"):
                scores[rel] += 2
                reasons[rel].append("test surface")
        for relationship in relationships:
            for source in relationship["sources"]:
                scores[source] += 3
                reasons[source].append("referenced by test")
        return [
            {"file": rel, "score": scores[rel], "reasons": sorted(set(reasons[rel]))}
            for rel in sorted(scores, key=lambda item: (-scores[item], item))[:50]
        ]

    def search(self, pattern: str, files: list[Path] | None = None, max_hits: int = 100) -> list[dict[str, Any]]:
        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise RepositoryInspectionError(f"Invalid search pattern: {exc}") from exc
        files = files if files is not None else self._files()[0]
        hits: list[dict[str, Any]] = []
        for path in files:
            if path.suffix.lower() not in _LANGUAGES:
                continue
            try:
                for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if regex.search(line):
                        hits.append({"file": self._rel(path), "line": line_number, "text": line.strip()[:240]})
                        if len(hits) >= max_hits:
                            return hits
            except OSError:
                continue
        return hits

    def inspect(self) -> dict[str, Any]:
        files, truncated = self._files()
        symbols = self.symbols(files)
        relationships = self.test_relationships(files)
        return {
            "root": str(self.root),
            "file_count": len(files),
            "truncated": truncated,
            "git": {"status": self.git_status(), "history": self.git_history(), "diff": self.git_diff()},
            "languages": self.languages(files),
            "package_managers": self.package_managers(files),
            "environments": self.environments(files),
            "test_frameworks": self.test_frameworks(files),
            "entry_points": self.entry_points(files),
            "important_files": self.important_files(files, relationships),
            "symbols": symbols,
            "test_relationships": relationships,
        }

