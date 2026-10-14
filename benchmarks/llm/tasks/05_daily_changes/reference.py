"""Trusted reference for 05_daily_changes."""
def solve(prices):
    return [prices[i] - prices[i - 1] for i in range(1, len(prices))]
