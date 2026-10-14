"""Random inputs for 03_cheapest_product. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 10)))
    return {"products": [{"name": "item%d" % i, "price": rng.randint(1, 6)} for i in range(n)]}
