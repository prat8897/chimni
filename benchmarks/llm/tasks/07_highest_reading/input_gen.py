"""Random inputs for 07_highest_reading. Called with a seeded random.Random."""


def generate(rng):
    return {"readings": [rng.randint(-20, 40) for _ in range(rng.choice([0] + list(range(1, 12))))]}
