"""Random inputs for 06_average_rating. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 12)))
    return {"reviews": [{"user": "u%d" % i, "stars": rng.randint(1, 5)} for i in range(n)]}
