from atelier.session import (
    _command_completions,
    _path_completion_input,
    _path_completion_request,
    _path_completions,
)


def test_path_completions_match_directories_and_add_slash(tmp_path) -> None:
    (tmp_path / "Downloads").mkdir()
    (tmp_path / "Downtown-notes.pdf").touch()
    (tmp_path / "Documents").mkdir()

    assert _path_completions("Dow", directories_only=True, cwd=tmp_path) == ["Downloads/"]
    assert _path_completions("Dow", cwd=tmp_path) == ["Downloads/", "Downtown-notes.pdf"]


def test_path_completions_preserve_home_prefix(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / "Documents").mkdir()
    monkeypatch.setenv("HOME", str(home))

    assert _path_completions("~/Doc", directories_only=True, cwd=tmp_path) == ["~/Documents/"]


def test_command_completions_include_atelier_and_terminal_commands() -> None:
    assert "doctor" in _command_completions("doc")
    assert "cd" in _command_completions("c")


def test_nested_workspace_and_repo_commands_request_directory_completion() -> None:
    assert _path_completion_request("workspace add ~/code_projects/", 29) == (True, True)
    assert _path_completion_request("atelier workspace add ~/code_projects/", 37) == (True, True)
    assert _path_completion_request("repo inspect ", 13) == (True, True)


def test_nested_path_completion_preserves_lookup_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    root = tmp_path / "code_projects" / "exam_website" / "daily"
    root.mkdir(parents=True)
    (root / "daily_questions").mkdir()

    line = "workspace add ~/code_projects/exam_website/da"
    begin = len("workspace add ~/code_projects/")
    lookup, replacement = _path_completion_input(line, begin, "exam_website/da")

    assert lookup == "~/code_projects/exam_website/da"
    assert replacement == "~/code_projects/"
    assert _path_completions(lookup, directories_only=True, cwd=tmp_path) == ["~/code_projects/exam_website/daily/"]
