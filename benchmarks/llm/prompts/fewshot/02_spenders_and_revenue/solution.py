def solve(orders, min_total):
    totals = {}
    for o in orders:
        totals[o["customer"]] = totals.get(o["customer"], 0) + o["amount"]
    big = sorted(((c, t) for c, t in totals.items() if t > min_total), key=lambda p: p[1], reverse=True)
    return big, sum(o["amount"] for o in orders)
