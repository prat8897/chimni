import pandas as pd


def solve(users, n):
    df = pd.DataFrame(users, columns=["name", "joined"])
    return df["name"].head(n).tolist()
