"""Trusted reference for 14_lowest_balance."""
def solve(transactions):
    if not transactions:
        return None
    balance, lowest = 0, None
    for t in transactions:
        balance += t["amount"]
        lowest = balance if lowest is None else min(lowest, balance)
    return lowest
