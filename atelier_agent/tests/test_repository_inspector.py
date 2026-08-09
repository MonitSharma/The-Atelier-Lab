from pathlib import Path

from repo.inspector import RepositoryInspector


FIXTURE = Path(__file__).parent / "fixtures" / "repo_fixture"


def test_inspector_reports_multi_file_repository_structure() -> None:
    profile = RepositoryInspector(FIXTURE).inspect()

    assert profile["file_count"] == 7
    assert profile["languages"]["Python"] == 5
    assert {item["manager"] for item in profile["package_managers"]} == {"Python / pyproject"}
    assert profile["test_frameworks"][0]["framework"] == "pytest"
    assert {item["name"] for item in profile["entry_points"]} >= {"fixture"}
    assert any(row["file"] == "src/samplepkg/core.py" for row in profile["symbols"])
    assert any(
        row["test"] == "tests/test_core.py" and "src/samplepkg/core.py" in row["sources"]
        for row in profile["test_relationships"]
    )
    assert any(item["file"] == "pyproject.toml" for item in profile["important_files"])


def test_inspector_search_is_deterministic() -> None:
    hits = RepositoryInspector(FIXTURE).search(r"def add")
    assert hits == [{"file": "src/samplepkg/core.py", "line": 1, "text": "def add(left: int, right: int) -> int:"}]
