import pandas as pd


def solve(players):
    df = pd.DataFrame(players, columns=["name", "score", "country"])
    df = df.sort_values(["score", "name"], ascending=[False, True], kind="stable")
    return list(df[["name", "score"]].itertuples(index=False, name=None))
