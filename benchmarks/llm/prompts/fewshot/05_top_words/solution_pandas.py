import pandas as pd


def solve(text, n):
    counts = pd.Series(text.lower().split(), dtype=object).value_counts(sort=False)
    return list(counts.sort_values(ascending=False, kind="stable").head(n).items())
