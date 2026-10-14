import pandas as pd


def solve(transactions):
    df = pd.DataFrame(transactions, columns=["type", "amount"])
    return int(df.loc[df["type"] == "refund", "amount"].sum())
