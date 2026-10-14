"""Trusted reference for 01_count_in_stock."""
def solve(products):
    return sum(1 for p in products if p["stock"] > 0)
