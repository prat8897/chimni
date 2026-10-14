import pandas as pd


def solve(sales):
    df = pd.DataFrame(sales, columns=["cat", "amount"])
    by_cat = df.groupby("cat", sort=False)["amount"].sum()
    return list((by_cat / df["amount"].sum()).items())
