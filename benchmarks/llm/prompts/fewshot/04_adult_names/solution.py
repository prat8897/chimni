def solve(users):
    return sorted(u["name"] for u in users if u["age"] >= 18)
