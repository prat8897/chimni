import pandas as pd


def solve(orders):
    df = pd.DataFrame(orders, columns=["customer", "amount"])
    counts = df.groupby("customer", sort=False).size()
    return list(counts.sort_values(ascending=False, kind="stable").items())
