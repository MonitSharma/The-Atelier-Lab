from inventory import line_total, order_total


def test_line_total():
    assert line_total({"price": 3, "quantity": 4}) == 12


def test_order_total():
    items = [{"price": 3, "quantity": 4}, {"price": 2.5, "quantity": 2}]
    assert order_total(items) == 17
