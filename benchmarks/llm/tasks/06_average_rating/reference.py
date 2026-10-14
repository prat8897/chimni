"""Trusted reference for 06_average_rating."""
def solve(reviews):
    if not reviews:
        return None
    return sum(r["stars"] for r in reviews) / len(reviews)
