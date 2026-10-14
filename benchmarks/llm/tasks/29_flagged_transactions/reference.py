"""Trusted reference for 29_flagged_transactions."""
def solve(transactions, limit):
    return [t["id"] for t in transactions if t["type"] == "refund" or t["amount"] > limit]
