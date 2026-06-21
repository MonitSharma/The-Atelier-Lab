def unique(items):
    return list(set(items))  # BUG: set conversion does not preserve first-seen order


def count_items(items):
    return len(items)
