"""Trusted reference for 24_top_customer_share."""
def solve(orders):
    if not orders:
        return None
    totals = {}
    for o in orders:
        totals[o["customer"]] = totals.get(o["customer"], 0) + o["amount"]
    return max(totals.values()) / sum(totals.values())
