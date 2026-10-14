"""Random inputs for 18_normalized_scores. Called with a seeded random.Random."""


def generate(rng):
    return {"scores": [rng.randint(1, 100) for _ in range(rng.choice([0] + list(range(1, 12))))]}
