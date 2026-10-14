"""Random inputs for 21_revenue_per_unit_by_category. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 12)))
    return {"sales": [{"category": rng.choice(["food", "toys", "books"]), "revenue": rng.randint(1, 500),
                       "units": rng.randint(1, 20)} for _ in range(n)]}
