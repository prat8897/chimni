"""Random inputs for 09_orders_per_customer. Called with a seeded random.Random."""


def generate(rng):
    names = ["asha", "ravi", "meera", "kiran", "dev"]
    n = rng.choice([0] + list(range(1, 14)))
    return {"orders": [{"customer": rng.choice(names), "amount": rng.randint(1, 99)} for _ in range(n)]}
