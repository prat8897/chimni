def adult_names(users):
    names = [u["name"] for u in users if u["age"] >= 18]
    return sorted(names)
