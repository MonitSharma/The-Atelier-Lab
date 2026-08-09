import json
import sqlite3

from files.artifacts import profile_path


def test_csv_profile_reports_schema_missingness_and_preview(tmp_path) -> None:
    path = tmp_path / "records.csv"
    path.write_text("name,score\nAlice,1\nBob,\n", encoding="utf-8")
    profile = profile_path(path)
    assert profile.kind == "csv"
    assert profile.shape == {"rows": 2, "columns": 2}
    assert {field["name"] for field in profile.schema} == {"name", "score"}
    assert profile.missingness["score"] == 1


def test_json_records_profile_is_tabular(tmp_path) -> None:
    path = tmp_path / "records.json"
    path.write_text(json.dumps([{"id": 1, "label": "a"}, {"id": 2, "label": "b"}]), encoding="utf-8")
    profile = profile_path(path)
    assert profile.kind == "json_records"
    assert profile.shape["rows"] == 2
    assert profile.schema[0]["type"] in {"number", "string"}


def test_sqlite_profile_reports_tables_and_columns(tmp_path) -> None:
    path = tmp_path / "sample.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE papers (id INTEGER PRIMARY KEY, title TEXT)")
        connection.execute("INSERT INTO papers VALUES (1, 'Atelier')")
    profile = profile_path(path)
    assert profile.kind == "sqlite"
    assert profile.shape["tables"] == 1
    assert profile.preview[0]["rows"] == 1

