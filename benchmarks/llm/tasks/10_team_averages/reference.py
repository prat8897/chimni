"""Trusted reference for 10_team_averages."""
def solve(players):
    by_team = {}
    for p in players:
        by_team.setdefault(p["team"], []).append(p["score"])
    return [(t, sum(s) / len(s)) for t, s in by_team.items()]
