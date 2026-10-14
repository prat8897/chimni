"""Random inputs for 25_grade_band_counts. Called with a seeded random.Random."""


def generate(rng):
    return {"scores": [rng.randint(50, 100) for _ in range(rng.choice([0] + list(range(1, 14))))]}
