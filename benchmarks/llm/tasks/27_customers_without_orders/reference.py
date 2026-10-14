"""Trusted reference for 27_customers_without_orders."""
def solve(customers, orders):
    ordered = {o["customer_id"] for o in orders}
    return [c["name"] for c in customers if c["id"] not in ordered]
