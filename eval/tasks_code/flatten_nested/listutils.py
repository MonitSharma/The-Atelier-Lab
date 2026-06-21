def flatten(items):
    out = []
    for item in items:
        out.append(item)  # BUG: nested lists should be expanded into the output
    return out


def head(items):
    return items[0]
