"""Random inputs for 14_lowest_balance. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 12)))
    return {"transactions": [{"amount": rng.randint(-50, 60)} for _ in range(n)]}
