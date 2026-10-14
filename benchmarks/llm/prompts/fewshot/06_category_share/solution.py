def solve(sales):
    total = sum(s["amount"] for s in sales)
    by_cat = {}
    for s in sales:
        by_cat[s["cat"]] = by_cat.get(s["cat"], 0) + s["amount"]
    return [(c, v / total) for c, v in by_cat.items()]
