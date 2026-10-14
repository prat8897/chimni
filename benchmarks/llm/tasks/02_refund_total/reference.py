"""Trusted reference for 02_refund_total."""
def solve(transactions):
    return sum(t["amount"] for t in transactions if t["type"] == "refund")
