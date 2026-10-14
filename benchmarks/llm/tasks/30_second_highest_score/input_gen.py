"""Random inputs for 30_second_highest_score. Called with a seeded random.Random."""


def generate(rng):
    return {"scores": [rng.randint(1, 8) for _ in range(rng.choice([0, 1] + list(range(2, 10))))]}
