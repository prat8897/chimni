import pandas as pd


def first_big_new_transaction(transactions, limit):
    df = pd.DataFrame(transactions, columns=["id", "amount"]).drop_duplicates("id")
    big = df.loc[df["amount"] > limit, "id"]
    return big.iloc[0] if len(big) else None
