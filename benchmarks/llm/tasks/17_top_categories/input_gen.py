"""Random inputs for 17_top_categories. Called with a seeded random.Random."""


def generate(rng):
    cats = ["toys", "food", "books", "garden", "tools"]
    k = rng.choice([0] + list(range(1, 15)))
    return {"items": [{"name": "i%d" % i, "category": rng.choice(cats)} for i in range(k)], "n": rng.randint(0, 4)}
