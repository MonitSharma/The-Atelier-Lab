from atelier.session import _command_completions, _path_completion_request, _path_completions


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
