import pandas as pd


def solve(visits):
    df = pd.DataFrame(visits, columns=["visitor", "page"])
    return int(df["visitor"].nunique())
