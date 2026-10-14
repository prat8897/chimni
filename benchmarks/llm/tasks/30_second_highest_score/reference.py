"""Trusted reference for 30_second_highest_score."""
def solve(scores):
    distinct = sorted(set(scores), reverse=True)
    return distinct[1] if len(distinct) >= 2 else None
