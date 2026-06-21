from pathlib import Path

from tools.files import run_read_file


def test_read_existing_file(tmp_path, monkeypatch) -> None:
    test_file = tmp_path / "sample.txt"
    test_file.write_text("hello from atelier", encoding="utf-8")

    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())

    result = run_read_file({"path": "sample.txt"})

    assert result["status"] == "success"
    assert result["tool"] == "read_file"
    assert result["content"] == "hello from atelier"


def test_read_missing_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())

    result = run_read_file({"path": "missing.txt"})

    assert result["status"] == "error"
    assert result["error_type"] == "file_not_found"


def test_reject_path_outside_workspace(tmp_path, monkeypatch) -> None:
    outside_dir = tmp_path.parent
    outside_file = outside_dir / "outside.txt"
    outside_file.write_text("secret", encoding="utf-8")

    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())

    result = run_read_file({"path": "../outside.txt"})

    assert result["status"] == "error"
    assert result["error_type"] == "path_not_allowed"


def test_reject_directory(tmp_path, monkeypatch) -> None:
    directory = tmp_path / "folder"
    directory.mkdir()

    monkeypatch.setattr("tools.files.PROJECT_ROOT", tmp_path.resolve())

    result = run_read_file({"path": "folder"})

    assert result["status"] == "error"
    assert result["error_type"] == "not_a_file"


def test_invalid_arguments() -> None:
    result = run_read_file({"wrong_key": "PROJECT.md"})

    assert result["status"] == "error"
    assert result["error_type"] == "invalid_arguments"
