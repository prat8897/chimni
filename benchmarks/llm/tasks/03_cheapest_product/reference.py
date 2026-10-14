"""Trusted reference for 03_cheapest_product."""
def solve(products):
    if not products:
        return None
    return min(products, key=lambda p: p["price"])["name"]
