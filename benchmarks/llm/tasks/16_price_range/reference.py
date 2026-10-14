"""Trusted reference for 16_price_range."""
def solve(products):
    if not products:
        return None
    prices = [p["price"] for p in products]
    return max(prices) - min(prices)
