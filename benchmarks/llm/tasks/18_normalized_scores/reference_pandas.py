import pandas as pd


def solve(scores):
    s = pd.Series(scores, dtype="int64")
    return (s / s.max()).tolist()
