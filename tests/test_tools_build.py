"""Tests for the build-mode tools (no model required)."""

from tools.code_exec import run_python
from tools.files import run_edit_file, run_read_file, run_write_file
from tools.repo_map import run_repo_map
from tools.search import run_search
from tools.test_runner import _parse_counts


def test_code_exec_runs_and_captures_stdout() -> None:
    r = run_python({"code": "print(6 * 7)"})
    assert r["status"] == "success"
    assert r["stdout"].strip() == "42"


def test_code_exec_timeout() -> None:
    r = run_python({"code": "while True:\n    pass", "timeout": 1})
    assert r["status"] == "error"
    assert r["error_type"] == "timeout"


def test_code_exec_nonzero_exit() -> None:
    r = run_python({"code": "raise SystemExit(3)"})
    assert r["status"] == "error"
    assert r["returncode"] == 3


def test_write_edit_read_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())

    w = run_write_file({"path": "note.txt", "content": "hello world"})
    assert w["status"] == "success"

    e = run_edit_file({"path": "note.txt", "old_string": "world", "new_string": "atelier"})
    assert e["status"] == "success"

    r = run_read_file({"path": "note.txt"})
    assert r["content"] == "hello atelier"


def test_edit_requires_unique_match(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    run_write_file({"path": "d.txt", "content": "x x x"})
    r = run_edit_file({"path": "d.txt", "old_string": "x", "new_string": "y"})
    assert r["status"] == "error"
    assert r["error_type"] == "string_not_unique"


def test_write_rejects_path_escape(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    r = run_write_file({"path": "../evil.txt", "content": "nope"})
    assert r["status"] == "error"
    assert r["error_type"] == "path_not_allowed"


def test_repo_map_outlines_python(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    (tmp_path / "m.py").write_text("def foo():\n    pass\n\nclass Bar:\n    def baz(self):\n        pass\n")
    r = run_repo_map({"path": "."})
    assert r["status"] == "success"
    assert "def foo()" in r["map"]
    assert "class Bar(baz)" in r["map"]


def test_search_finds_pattern(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    (tmp_path / "a.py").write_text("alpha = 1\nbeta = 2\n")
    r = run_search({"pattern": r"beta", "path": "."})
    assert r["status"] == "success"
    assert any("beta" in h["text"] for h in r["hits"])


def test_test_runner_parser() -> None:
    counts = _parse_counts("5 passed, 1 failed, 2 skipped in 0.40s")
    assert counts == {"passed": 5, "failed": 1, "error": 0, "skipped": 2}
