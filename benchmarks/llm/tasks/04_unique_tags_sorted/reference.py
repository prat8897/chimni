"""Trusted reference for 04_unique_tags_sorted."""
def solve(tags):
    return sorted(set(t.lower() for t in tags))
