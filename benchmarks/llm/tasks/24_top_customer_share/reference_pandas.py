import pandas as pd


def solve(orders):
    df = pd.DataFrame(orders, columns=["customer", "amount"])
    if df.empty:
        return None
    return float(df.groupby("customer")["amount"].sum().max() / df["amount"].sum())
