# Category share

**Inputs**
- `sales`: a list of records, each with `cat` (text) and `amount` (integer, 1 or more).

**Output**
- A list of (cat, share) pairs: for each category, its total `amount` divided by the total `amount` of all sales.
  Categories appear in the order in which each first appears in `sales`.
