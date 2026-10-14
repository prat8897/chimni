"""Random inputs for 26_loyal_customer_names. Called with a seeded random.Random."""


def generate(rng):
    names = ["zoya", "asha", "ravi", "meera", "kiran", "dev"]
    rng.shuffle(names)
    k = rng.randint(0, 6)
    customers = [{"id": i + 1, "name": names[i]} for i in range(k)]
    orders = [{"customer_id": rng.randint(1, 8), "amount": rng.randint(1, 100)} for _ in range(rng.randint(0, 12))]
    return {"customers": customers, "orders": orders, "min_total": rng.randint(0, 200)}
