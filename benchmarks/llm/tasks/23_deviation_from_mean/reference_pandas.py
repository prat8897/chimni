import pandas as pd


def solve(measurements):
    s = pd.Series(measurements, dtype="int64")
    return (s - s.mean()).tolist()
