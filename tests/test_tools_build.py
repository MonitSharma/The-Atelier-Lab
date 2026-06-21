"""Tests for the build-mode tools (no model required)."""

from tools.ast_edit import run_ast_edit
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


def test_write_reports_python_syntax(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    ok = run_write_file({"path": "good.py", "content": "def f():\n    return 1\n"})
    assert ok["syntax_ok"] is True

    bad = run_write_file({"path": "bad.py", "content": "def f():\nreturn 1\n"})
    assert bad["status"] == "success"        # the write still happens
    assert bad["syntax_ok"] is False         # but the agent is warned
    assert "syntax_error" in bad


def test_edit_reports_broken_syntax(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    run_write_file({"path": "m.py", "content": "def f():\n    return 1\n"})
    # Replace the indented body with an unindented line -> breaks the function.
    r = run_edit_file({"path": "m.py", "old_string": "    return 1", "new_string": "return 1"})
    assert r["syntax_ok"] is False


def test_ast_edit_replaces_multiline_function_body(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    path = tmp_path / "statsutils.py"
    path.write_text(
        "def median(xs):\n"
        "    xs = sorted(xs)\n"
        "    n = len(xs)\n"
        "    return xs[n // 2]\n"
    )

    r = run_ast_edit({
        "path": "statsutils.py",
        "function_name": "median",
        "new_body": (
            "xs = sorted(xs)\n"
            "n = len(xs)\n"
            "if n % 2:\n"
            "    return xs[n // 2]\n"
            "return (xs[n // 2 - 1] + xs[n // 2]) / 2"
        ),
    })

    assert r["status"] == "success"
    assert r["syntax_ok"] is True
    namespace = {}
    exec(path.read_text(), namespace)
    assert namespace["median"]([1, 2, 3, 4]) == 2.5


def test_ast_edit_rejects_invalid_body_without_writing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    path = tmp_path / "m.py"
    original = "def f():\n    return 1\n"
    path.write_text(original)

    r = run_ast_edit({"path": "m.py", "function_name": "f", "new_body": "if True\n    return 2"})

    assert r["status"] == "error"
    assert r["error_type"] == "syntax_error"
    assert path.read_text() == original


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


def test_repo_map_uses_workspace_relative_paths_for_subdirs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    subdir = tmp_path / "task"
    subdir.mkdir()
    (subdir / "m.py").write_text("def foo():\n    pass\n")

    r = run_repo_map({"path": "task"})

    assert r["status"] == "success"
    assert "task/m.py" in r["map"]


def test_search_finds_pattern(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())
    (tmp_path / "a.py").write_text("alpha = 1\nbeta = 2\n")
    r = run_search({"pattern": r"beta", "path": "."})
    assert r["status"] == "success"
    assert any("beta" in h["text"] for h in r["hits"])


def test_test_runner_parser() -> None:
    counts = _parse_counts("5 passed, 1 failed, 2 skipped in 0.40s")
    assert counts == {"passed": 5, "failed": 1, "error": 0, "skipped": 2}
