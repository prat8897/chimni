def first_big_new_transaction(transactions, limit):
    seen = set()
    for t in transactions:
        if t["id"] in seen:
            continue
        seen.add(t["id"])
        if t["amount"] > limit:
            return t["id"]
    return None
