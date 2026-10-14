import pandas as pd


def solve(transactions, limit):
    df = pd.DataFrame(transactions, columns=["id", "type", "amount"])
    return df.loc[(df["type"] == "refund") | (df["amount"] > limit), "id"].tolist()
