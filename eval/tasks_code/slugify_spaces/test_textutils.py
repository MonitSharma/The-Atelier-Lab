from textutils import slugify, title_words


def test_slugify_removes_duplicate_and_edge_separators():
    assert slugify(" Hello,   World!! ") == "hello-world"
    assert slugify("Already clean") == "already-clean"


def test_title_words():
    assert title_words("hello world") == "Hello World"
