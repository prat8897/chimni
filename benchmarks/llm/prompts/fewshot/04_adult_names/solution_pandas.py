import pandas as pd


def solve(users):
    df = pd.DataFrame(users, columns=["name", "age"])
    return sorted(df.loc[df["age"] >= 18, "name"])
