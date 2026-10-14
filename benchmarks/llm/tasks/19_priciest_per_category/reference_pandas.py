import pandas as pd


def solve(products):
    df = pd.DataFrame(products, columns=["name", "category", "price"])
    idx = df.groupby("category", sort=False)["price"].idxmax()
    return list(df.loc[idx, ["category", "name"]].itertuples(index=False, name=None))
