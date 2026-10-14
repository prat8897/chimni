import pandas as pd


def solve(products):
    df = pd.DataFrame(products, columns=["name", "stock"])
    return int((df["stock"] > 0).sum())
