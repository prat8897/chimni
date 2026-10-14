import pandas as pd


def solve(scores):
    distinct = pd.Series(scores, dtype="int64").drop_duplicates().nlargest(2)
    return int(distinct.iloc[1]) if len(distinct) == 2 else None
