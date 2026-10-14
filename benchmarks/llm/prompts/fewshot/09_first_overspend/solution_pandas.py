import pandas as pd


def solve(expenses, budget):
    running = pd.Series(expenses, dtype="int64").cumsum()
    over = running[running > budget]
    return int(over.index[0]) if len(over) else None
