import pandas as pd


def top_words(text, n):
    counts = pd.Series(text.lower().split(), dtype=object).value_counts(sort=False)
    return list(counts.sort_values(ascending=False, kind="stable").head(n).items())
