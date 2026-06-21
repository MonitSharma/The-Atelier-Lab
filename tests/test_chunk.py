from rag.chunk import split_markdown, split_plain


def test_markdown_carries_heading_breadcrumb() -> None:
    text = "# Top\n\nintro\n\n## Sub\n\nbody about embeddings\n"
    chunks = split_markdown(text, source="notes.md")

    assert chunks, "expected at least one chunk"
    sub = [c for c in chunks if "embeddings" in c.text][0]
    assert sub.metadata["section"] == "Top > Sub"
    assert sub.text.startswith("[Top > Sub]")


def test_plain_windowing_respects_size_and_overlap() -> None:
    paras = "\n\n".join(f"paragraph number {i} with some words" for i in range(20))
    chunks = split_plain(paras, source="x.txt", size=120, overlap=20)

    assert len(chunks) > 1
    assert all(c.source == "x.txt" for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_huge_paragraph_is_hard_split() -> None:
    big = "word " * 1000  # one giant paragraph, no blank lines
    chunks = split_plain(big, source="x.txt", size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(c.text) <= 200 for c in chunks)
