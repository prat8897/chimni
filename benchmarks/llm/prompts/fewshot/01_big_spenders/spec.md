# Big spenders

Find the customers who spent more than a threshold, biggest first.

**Inputs**
- `orders`: a list of records, each with `customer` (text) and `amount` (integer).
- `min_total`: an integer.

**Output**
- A list of (customer, total) pairs: each customer whose orders' `amount` adds up to more than `min_total`, with that
  total, sorted by total from highest to lowest.

**Edge cases**
- Customers with equal totals keep the order in which each customer first appears in `orders`.
