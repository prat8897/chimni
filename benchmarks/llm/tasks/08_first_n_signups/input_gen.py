"""Random inputs for 08_first_n_signups. Called with a seeded random.Random."""


def generate(rng):
    k = rng.choice([0] + list(range(1, 10)))
    return {"users": [{"name": "user%d" % i, "joined": i * 3} for i in range(k)], "n": rng.randint(0, 6)}
