"""Random inputs for 28_median_time. Called with a seeded random.Random."""


def generate(rng):
    return {"times": [rng.randint(10, 500) for _ in range(rng.choice([0] + list(range(1, 12))))]}
