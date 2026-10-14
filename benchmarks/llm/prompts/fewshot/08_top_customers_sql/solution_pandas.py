import pandas as pd


def solve(customers, orders):
    c = pd.DataFrame(customers, columns=["id", "name"]).reset_index()
    o = pd.DataFrame(orders, columns=["id", "cid", "amount"])
    m = c.merge(o, left_on="id", right_on="cid").sort_values("index", kind="stable")
    totals = m.groupby("name", sort=False)["amount"].sum()
    return list(totals.sort_values(ascending=False, kind="stable").head(3).items())
