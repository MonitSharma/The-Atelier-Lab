def merge_defaults(defaults, overrides):
    defaults.update(overrides)  # BUG: should not mutate the defaults mapping
    return defaults


def has_key(mapping, key):
    return key in mapping
