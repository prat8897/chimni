import pandas as pd


def solve(sales):
    df = pd.DataFrame(sales, columns=["category", "revenue", "units"])
    g = df.groupby("category", sort=False)[["revenue", "units"]].sum()
    return list((g["revenue"] / g["units"]).items())
