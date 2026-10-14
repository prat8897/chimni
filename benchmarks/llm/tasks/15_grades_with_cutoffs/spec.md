# Grades with given cut-offs

Turn scores into letter grades using the given cut-offs.

**Inputs**
- `scores`: a list of integers.
- `a_cut`, `b_cut`: integers, with `a_cut` greater than `b_cut`.

**Output**
- A list of texts, one per score in the same order: `"A"` if the score is at least `a_cut`, otherwise `"B"` if it is
  at least `b_cut`, otherwise `"F"`.
