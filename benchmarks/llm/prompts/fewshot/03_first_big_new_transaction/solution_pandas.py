import pandas as pd


def solve(transactions, limit):
    df = pd.DataFrame(transactions, columns=["id", "amount"]).drop_duplicates("id")
    big = df.loc[df["amount"] > limit, "id"]
    return big.iloc[0] if len(big) else None
