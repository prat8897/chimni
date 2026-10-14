"""Trusted reference for 08_first_n_signups."""
def solve(users, n):
    return [u["name"] for u in users[:n]]
