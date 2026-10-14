import pandas as pd


def solve(tags):
    return sorted(pd.Series(tags, dtype=object).str.lower().unique())
