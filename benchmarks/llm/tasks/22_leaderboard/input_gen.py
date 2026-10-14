"""Random inputs for 22_leaderboard. Called with a seeded random.Random."""


def generate(rng):
    names = ["zed", "amy", "bob", "kai", "lia", "max", "ned"]
    n = rng.choice([0] + list(range(1, 10)))
    return {"players": [{"name": rng.choice(names), "score": rng.randint(1, 5), "country": rng.choice(["in", "us"])}
                        for _ in range(n)]}
