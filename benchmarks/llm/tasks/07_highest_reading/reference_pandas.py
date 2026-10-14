import pandas as pd


def solve(readings):
    if not readings:
        return None
    return int(pd.Series(readings).max())
