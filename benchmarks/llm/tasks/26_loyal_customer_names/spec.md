# Loyal customers

Name the customers who have spent at least `min_total`.

**Inputs**
- `customers`: a list of records, each with `id` (integer) and `name` (text). Names are unique.
- `orders`: a list of records, each with `customer_id` (integer) and `amount` (integer).
- `min_total`: an integer.

**Output**
- A list of texts, sorted in ascending order: the `name` of every customer who has at least one order and whose
  orders' `amount` adds up to at least `min_total`.

**Edge cases**
- Orders whose `customer_id` matches no customer are ignored.
