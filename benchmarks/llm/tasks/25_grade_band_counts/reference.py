"""Trusted reference for 25_grade_band_counts."""
def solve(scores):
    counts = {}
    for s in scores:
        g = "A" if s >= 90 else "B" if s >= 75 else "C"
        counts[g] = counts.get(g, 0) + 1
    return list(counts.items())
