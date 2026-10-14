# Top customer's share of revenue

What fraction of all revenue comes from the single biggest customer?

**Inputs**
- `orders`: a list of records, each with `customer` (text) and `amount` (integer, 1 or more).

**Output**
- A number: the largest per-customer total of `amount`, divided by the total `amount` of all orders. None (null) if
  there are no orders.
