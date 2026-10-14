import pandas as pd


def solve(products, sales):
    p = pd.DataFrame(products, columns=["id", "name"])
    s = pd.DataFrame(sales, columns=["product_id", "units"])
    # an inner merge does not promise to keep `products` order, and ties must follow it
    m = p.reset_index().merge(s, left_on="id", right_on="product_id").sort_values("index", kind="stable")
    totals = m.groupby("name", sort=False)["units"].sum()
    return list(totals.sort_values(ascending=False, kind="stable").items())
