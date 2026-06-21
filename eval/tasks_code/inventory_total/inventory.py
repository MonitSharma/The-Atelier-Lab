def line_total(item):
    return item["price"] + item["quantity"]  # BUG: quantity should multiply price


def order_total(items):
    return sum(line_total(item) for item in items)
