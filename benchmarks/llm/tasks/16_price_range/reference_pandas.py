import pandas as pd


def solve(products):
    df = pd.DataFrame(products, columns=["name", "price"])
    if df.empty:
        return None
    return int(df["price"].max() - df["price"].min())
