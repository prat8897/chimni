# Customers without orders

Find customers who have never ordered.

**Inputs**
- `customers`: a list of records, each with `id` (integer) and `name` (text).
- `orders`: a list of records, each with `customer_id` (integer) and `amount` (integer).

**Output**
- A list of texts: the `name` of every customer whose `id` appears in no order's `customer_id`, in `customers` order.
