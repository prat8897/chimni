"""Trusted reference for 20_inventory_value."""
def solve(items):
    return sum(i["price"] * i["qty"] for i in items)
