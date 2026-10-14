import pandas as pd


def solve(transactions):
    df = pd.DataFrame(transactions, columns=["amount"])
    if df.empty:
        return None
    return int(df["amount"].cumsum().min())
