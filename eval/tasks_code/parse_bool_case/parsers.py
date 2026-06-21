def parse_bool(text):
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(f"not a boolean: {text}")


def parse_int(text):
    return int(text.strip())
