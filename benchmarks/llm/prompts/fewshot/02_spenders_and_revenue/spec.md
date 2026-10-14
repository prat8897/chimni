# Big spenders and revenue

Two answers from the same orders.

**Inputs**
- `orders`: a list of records, each with `customer` (text) and `amount` (integer).
- `min_total`: an integer.

**Output**
- Two values:
  1. a list of (customer, total) pairs: each customer whose orders add up to more than `min_total`, sorted by total
     from highest to lowest (equal totals keep first-appearance order);
  2. an integer: the sum of `amount` over all orders.
