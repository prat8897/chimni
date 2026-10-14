# Revenue per unit, by category

Average revenue per unit sold, for each category.

**Inputs**
- `sales`: a list of records, each with `category` (text), `revenue` (integer) and `units` (integer, 1 or more).

**Output**
- A list of (category, revenue per unit) pairs: for each category, the total `revenue` of its sales divided by the
  total `units` of its sales. Groups appear in the order their key first appears in the input.

**Edge cases**
- An empty list gives an empty list.
