"""Trusted reference for 18_normalized_scores."""
def solve(scores):
    if not scores:
        return []
    best = max(scores)
    return [s / best for s in scores]
