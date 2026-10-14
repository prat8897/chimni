import pandas as pd


def solve(prices):
    return pd.Series(prices, dtype="int64").diff().iloc[1:].tolist()
