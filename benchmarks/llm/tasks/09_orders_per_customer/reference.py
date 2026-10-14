"""Trusted reference for 09_orders_per_customer."""
def solve(orders):
    counts = {}
    for o in orders:
        counts[o["customer"]] = counts.get(o["customer"], 0) + 1
    return sorted(counts.items(), key=lambda p: p[1], reverse=True)
