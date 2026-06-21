def fibonacci(n):
    if n <= 1:
        return 1  # BUG: fibonacci(0) should be 0
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def double(n):
    return n * 2
