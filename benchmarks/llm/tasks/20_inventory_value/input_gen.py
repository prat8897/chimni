"""Random inputs for 20_inventory_value. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 10)))
    return {"items": [{"name": "i%d" % k, "price": rng.randint(1, 30), "qty": rng.randint(0, 9)} for k in range(n)]}
