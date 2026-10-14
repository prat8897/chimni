# Most expensive product per category

For each category, name its most expensive product.

**Inputs**
- `products`: a list of records, each with `name` (text), `category` (text) and `price` (integer).

**Output**
- A list of (category, name) pairs: one per category, naming the product with the highest `price` in that category.
  Groups appear in the order their key first appears in the input.

**Edge cases**
- If several products in a category share the highest price, name the one that comes first in the list.
