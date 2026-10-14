"""Random inputs for 15_grades_with_cutoffs. Called with a seeded random.Random."""


def generate(rng):
    b = rng.randint(30, 70)
    return {"scores": [rng.randint(0, 100) for _ in range(rng.choice([0] + list(range(1, 12))))],
            "a_cut": rng.randint(b + 1, 100), "b_cut": b}
