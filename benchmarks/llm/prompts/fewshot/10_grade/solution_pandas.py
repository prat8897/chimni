import pandas as pd


def solve(score):
    return pd.cut([score], bins=[float("-inf"), 75, 90, float("inf")], right=False, labels=["C", "B", "A"])[0]
