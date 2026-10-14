"""Random inputs for 02_refund_total. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 12)))
    return {"transactions": [{"type": rng.choice(["sale", "sale", "refund", "fee"]), "amount": rng.randint(1, 200)}
                             for _ in range(n)]}
