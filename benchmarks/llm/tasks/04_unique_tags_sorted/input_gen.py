"""Random inputs for 04_unique_tags_sorted. Called with a seeded random.Random."""


def generate(rng):
    words = ["news", "News", "SPORT", "sport", "art", "Art", "tech", "TECH", "food"]
    return {"tags": [rng.choice(words) for _ in range(rng.choice([0] + list(range(1, 12))))]}
