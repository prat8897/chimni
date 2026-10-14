"""Random inputs for 27_customers_without_orders. Called with a seeded random.Random."""


def generate(rng):
    k = rng.randint(0, 7)
    customers = [{"id": i + 1, "name": "c%d" % (i + 1)} for i in range(k)]
    orders = [{"customer_id": rng.randint(1, 9), "amount": rng.randint(1, 50)} for _ in range(rng.randint(0, 8))]
    return {"customers": customers, "orders": orders}
