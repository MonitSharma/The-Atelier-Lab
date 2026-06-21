import re


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text  # BUG: trailing separators should be removed


def title_words(text):
    return " ".join(word.capitalize() for word in text.split())
