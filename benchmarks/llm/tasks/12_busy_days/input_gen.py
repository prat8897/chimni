"""Random inputs for 12_busy_days. Called with a seeded random.Random."""


def generate(rng):
    days = ["mon", "tue", "wed", "thu", "fri"]
    n = rng.choice([0] + list(range(1, 15)))
    return {"events": [{"day": rng.choice(days), "kind": rng.choice(["call", "mail"])} for _ in range(n)],
            "k": rng.randint(0, 4)}
