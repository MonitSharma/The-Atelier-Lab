DEFAULTS = {"limit": 3, "enabled": True}


def load_config(overrides=None):
    """Return an independent, normalized configuration."""
    values = DEFAULTS
    if overrides:
        values.update(overrides)
    return values
