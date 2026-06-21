def clamp(value, lower, upper):
    return min(lower, max(value, upper))  # BUG: lower/upper are applied in the wrong order


def percent(part, whole):
    return part / whole * 100
