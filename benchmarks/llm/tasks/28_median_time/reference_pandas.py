import pandas as pd


def solve(times):
    if not times:
        return None
    return float(pd.Series(times).median())
