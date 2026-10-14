"""Trusted reference for 15_grades_with_cutoffs."""
def solve(scores, a_cut, b_cut):
    return ["A" if s >= a_cut else "B" if s >= b_cut else "F" for s in scores]
