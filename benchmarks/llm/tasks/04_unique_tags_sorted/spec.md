# Unique tags

List the distinct tags, case-insensitively.

**Inputs**
- `tags`: a list of texts (ASCII letters, mixed case).

**Output**
- A list of texts: every tag converted to lowercase, with duplicates removed, sorted in ascending order.

**Edge cases**
- An empty list gives an empty list. `"News"` and `"news"` count as the same tag.
