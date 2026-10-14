import numpy as np
import pandas as pd


def solve(scores, a_cut, b_cut):
    s = pd.Series(scores, dtype="int64")
    return np.where(s >= a_cut, "A", np.where(s >= b_cut, "B", "F")).tolist()
