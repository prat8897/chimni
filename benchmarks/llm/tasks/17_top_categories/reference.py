"""Trusted reference for 17_top_categories."""
def solve(items, n):
    counts = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    return sorted(counts.items(), key=lambda p: p[1], reverse=True)[:n]
