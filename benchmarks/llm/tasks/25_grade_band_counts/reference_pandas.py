import numpy as np
import pandas as pd


def solve(scores):
    s = pd.Series(scores, dtype="int64")
    grades = pd.Series(np.where(s >= 90, "A", np.where(s >= 75, "B", "C")), dtype=object)
    return list(grades.groupby(grades, sort=False).size().items())
