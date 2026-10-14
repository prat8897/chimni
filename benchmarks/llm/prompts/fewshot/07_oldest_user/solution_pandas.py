import pandas as pd


def solve(users):
    df = pd.DataFrame(users, columns=["name", "age"])
    if df.empty:
        return None
    return df.loc[df["age"].idxmax(), "name"]
