import pandas as pd


def solve(events, k):
    df = pd.DataFrame(events, columns=["day", "kind"])
    counts = df.groupby("day", sort=False).size()
    return list(counts[counts > k].index)
