"""Random inputs for 19_priciest_per_category. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 14)))
    return {"products": [{"name": "p%d" % i, "category": rng.choice(["a", "b", "c"]), "price": rng.randint(1, 8)}
                         for i in range(n)]}
