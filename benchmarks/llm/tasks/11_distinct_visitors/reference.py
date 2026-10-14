"""Trusted reference for 11_distinct_visitors."""
def solve(visits):
    return len({v["visitor"] for v in visits})
