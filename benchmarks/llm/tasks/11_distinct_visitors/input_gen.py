"""Random inputs for 11_distinct_visitors. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 15)))
    return {"visits": [{"visitor": rng.randint(1, 6), "page": rng.choice(["/", "/a", "/b"])} for _ in range(n)]}
