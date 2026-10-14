def solve(customers, orders):
    totals = {}
    for c in customers:
        for o in orders:
            if o["cid"] == c["id"]:
                totals[c["name"]] = totals.get(c["name"], 0) + o["amount"]
    return sorted(totals.items(), key=lambda p: p[1], reverse=True)[:3]
