# Orders per customer

Count orders per customer, busiest first.

**Inputs**
- `orders`: a list of records, each with `customer` (text) and `amount` (integer).

**Output**
- A list of (customer, count) pairs: each customer that appears, with how many orders they placed, sorted by count
  from highest to lowest.

**Edge cases**
- Customers with the same count keep the order in which each customer first appears in `orders`.
- An empty list gives an empty list.
