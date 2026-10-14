"""Random inputs for 16_price_range. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 10)))
    return {"products": [{"name": "p%d" % i, "price": rng.randint(1, 100)} for i in range(n)]}
