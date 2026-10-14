import pandas as pd


def solve(customers, orders):
    c = pd.DataFrame(customers, columns=["id", "name"])
    o = pd.DataFrame(orders, columns=["customer_id", "amount"])
    return c.loc[~c["id"].isin(o["customer_id"]), "name"].tolist()
