"""Trusted reference for 12_busy_days."""
def solve(events, k):
    counts = {}
    for e in events:
        counts[e["day"]] = counts.get(e["day"], 0) + 1
    return [d for d, c in counts.items() if c > k]
