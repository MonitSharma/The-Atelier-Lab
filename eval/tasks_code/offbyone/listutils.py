def first_n(items, n):
    return items[: n - 1]  # BUG: off-by-one, drops the last element


def last(items):
    return items[-1]
