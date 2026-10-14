"""Random inputs for 13_units_sold_by_product. Called with a seeded random.Random."""


def generate(rng):
    names = ["pen", "ink", "pad", "cup", "mug", "bag"]
    rng.shuffle(names)
    k = rng.randint(0, 6)
    products = [{"id": i + 1, "name": names[i]} for i in range(k)]
    sales = [{"product_id": rng.randint(1, 8), "units": rng.randint(1, 5)} for _ in range(rng.randint(0, 12))]
    return {"products": products, "sales": sales}
