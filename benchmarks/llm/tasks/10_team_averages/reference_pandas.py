import pandas as pd


def solve(players):
    df = pd.DataFrame(players, columns=["name", "team", "score"])
    return list(df.groupby("team", sort=False)["score"].mean().items())
