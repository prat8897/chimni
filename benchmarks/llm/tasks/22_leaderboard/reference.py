"""Trusted reference for 22_leaderboard."""
def solve(players):
    ranked = sorted(players, key=lambda p: (-p["score"], p["name"]))
    return [(p["name"], p["score"]) for p in ranked]
