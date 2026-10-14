import pandas as pd


def solve(customers, orders, min_total):
    c = pd.DataFrame(customers, columns=["id", "name"])
    o = pd.DataFrame(orders, columns=["customer_id", "amount"])
    totals = c.merge(o, left_on="id", right_on="customer_id").groupby("name")["amount"].sum()
    return sorted(totals[totals >= min_total].index)
