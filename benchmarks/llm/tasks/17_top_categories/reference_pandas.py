import pandas as pd


def solve(items, n):
    df = pd.DataFrame(items, columns=["name", "category"])
    counts = df.groupby("category", sort=False).size()
    return list(counts.sort_values(ascending=False, kind="stable").head(n).items())
