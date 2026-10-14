import pandas as pd


def solve(orders, min_total):
    df = pd.DataFrame(orders, columns=["customer", "amount"])
    totals = df.groupby("customer", sort=False)["amount"].sum()
    totals = totals[totals > min_total].sort_values(ascending=False, kind="stable")
    return list(totals.items())
