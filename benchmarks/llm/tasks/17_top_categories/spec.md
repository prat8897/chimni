# Top categories by item count

The `n` categories with the most items.

**Inputs**
- `items`: a list of records, each with `name` (text) and `category` (text).
- `n`: an integer, 0 or more.

**Output**
- A list of (category, count) pairs: the `n` categories with the most items, with their item counts, sorted by count
  from highest to lowest. Fewer than `n` if there are fewer categories.

**Edge cases**
- Categories with the same count keep the order in which each category first appears in `items`.
