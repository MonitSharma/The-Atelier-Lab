def moving_average(values, window):
    return [
        sum(values[i : i + window]) / window
        for i in range(len(values) - window)  # BUG: misses the final complete window
    ]


def latest(values):
    return values[-1]
