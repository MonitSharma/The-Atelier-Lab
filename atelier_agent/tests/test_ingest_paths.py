from rag.ingest import iter_files


def test_explicit_root_inside_data_is_not_skipped(tmp_path):
    root = tmp_path / "data" / "corpus" / "papers"
    root.mkdir(parents=True)

    paper = root / "example.txt"
    paper.write_text("scientific content", encoding="utf-8")

    assert list(iter_files(root)) == [paper]


def test_nested_junk_directory_is_still_skipped(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()

    good = root / "paper.txt"
    good.write_text("keep me", encoding="utf-8")

    junk = root / "build"
    junk.mkdir()
    ignored = junk / "generated.txt"
    ignored.write_text("ignore me", encoding="utf-8")

    assert list(iter_files(root)) == [good]
