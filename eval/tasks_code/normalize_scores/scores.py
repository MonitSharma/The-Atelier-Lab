def normalize(scores):
    highest = max(scores)
    return [score / highest for score in scores]  # BUG: should min-max normalize to 0..1


def best(scores):
    return max(scores)
