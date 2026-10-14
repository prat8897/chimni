# Top customers

**Inputs**
- `customers`: a list of records, each with `id` (integer) and `name` (text).
- `orders`: a list of records, each with `id` (integer), `cid` (integer, a customer id) and `amount` (integer).

**Output**
- A list of at most 3 (name, total) pairs: join each order to the customer whose `id` equals the order's `cid`
  (orders with no matching customer are ignored), add up `amount` per customer `name`, and keep the three largest
  totals, highest first. Equal totals keep the order of the customers in `customers`.
