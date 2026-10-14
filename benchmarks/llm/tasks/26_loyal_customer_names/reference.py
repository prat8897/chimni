"""Trusted reference for 26_loyal_customer_names."""
def solve(customers, orders, min_total):
    totals = {}
    for c in customers:
        for o in orders:
            if o["customer_id"] == c["id"]:
                totals[c["name"]] = totals.get(c["name"], 0) + o["amount"]
    return sorted(n for n, t in totals.items() if t >= min_total)
