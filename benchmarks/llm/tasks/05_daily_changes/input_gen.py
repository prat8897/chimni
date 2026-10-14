"""Random inputs for 05_daily_changes. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0, 1] + list(range(2, 12)))
    return {"prices": [rng.randint(80, 120) for _ in range(n)]}
