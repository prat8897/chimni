def oldest_user(users):
    if not users:
        return None
    return max(users, key=lambda u: u["age"])["name"]
