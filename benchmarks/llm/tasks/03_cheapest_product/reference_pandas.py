import pandas as pd


def solve(products):
    df = pd.DataFrame(products, columns=["name", "price"])
    if df.empty:
        return None
    return df.loc[df["price"].idxmin(), "name"]
