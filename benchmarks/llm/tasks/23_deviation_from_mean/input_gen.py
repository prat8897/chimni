"""Random inputs for 23_deviation_from_mean. Called with a seeded random.Random."""


def generate(rng):
    return {"measurements": [rng.randint(-10, 30) for _ in range(rng.choice([0] + list(range(1, 12))))]}
