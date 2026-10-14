# Inventory value

What is the stock worth?

**Inputs**
- `items`: a list of records, each with `name` (text), `price` (integer) and `qty` (integer).

**Output**
- An integer: the sum over all items of `price` × `qty`.

**Edge cases**
- An empty list gives 0.
