"""Random inputs for 24_top_customer_share. Called with a seeded random.Random."""


def generate(rng):
    n = rng.choice([0] + list(range(1, 12)))
    return {"orders": [{"customer": rng.choice(["asha", "ravi", "meera", "dev"]), "amount": rng.randint(1, 200)}
                       for _ in range(n)]}
