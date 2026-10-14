"""Random inputs for 10_team_averages. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 14)))
    return {"players": [{"name": "p%d" % i, "team": rng.choice(["red", "blue", "green"]), "score": rng.randint(0, 50)}
                        for i in range(n)]}
