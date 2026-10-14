import pandas as pd


def solve(items):
    df = pd.DataFrame(items, columns=["name", "price", "qty"])
    return int((df["price"] * df["qty"]).sum())
