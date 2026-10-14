"""Random inputs for 01_count_in_stock. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 12)))
    return {"products": [{"name": "p%d" % i, "stock": rng.choice([0, 0, 1, 2, 5, 9])} for i in range(n)]}
