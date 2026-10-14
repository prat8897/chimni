"""Trusted reference for 19_priciest_per_category."""
def solve(products):
    best = {}
    for p in products:
        c = p["category"]
        if c not in best or p["price"] > best[c]["price"]:
            best[c] = p
    return [(c, p["name"]) for c, p in best.items()]
