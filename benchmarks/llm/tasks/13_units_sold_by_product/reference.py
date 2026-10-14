"""Trusted reference for 13_units_sold_by_product."""
def solve(products, sales):
    totals = {}
    for p in products:
        for s in sales:
            if s["product_id"] == p["id"]:
                totals[p["name"]] = totals.get(p["name"], 0) + s["units"]
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
