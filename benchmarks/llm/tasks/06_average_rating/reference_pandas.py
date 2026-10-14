import pandas as pd


def solve(reviews):
    df = pd.DataFrame(reviews, columns=["user", "stars"])
    if df.empty:
        return None
    return float(df["stars"].mean())
