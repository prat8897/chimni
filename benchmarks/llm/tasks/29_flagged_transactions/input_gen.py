"""Random inputs for 29_flagged_transactions. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 12)))
    return {"transactions": [{"id": i, "type": rng.choice(["sale", "sale", "refund"]), "amount": rng.randint(1, 100)}
                             for i in range(n)], "limit": rng.randint(0, 100)}
