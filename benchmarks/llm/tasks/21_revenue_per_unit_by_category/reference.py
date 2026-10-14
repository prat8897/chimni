"""Trusted reference for 21_revenue_per_unit_by_category."""
def solve(sales):
    rev, units = {}, {}
    for s in sales:
        c = s["category"]
        rev[c] = rev.get(c, 0) + s["revenue"]
        units[c] = units.get(c, 0) + s["units"]
    return [(c, rev[c] / units[c]) for c in rev]
