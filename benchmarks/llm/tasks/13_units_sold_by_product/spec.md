# Units sold per product

Total units sold for each product, best sellers first.

**Inputs**
- `products`: a list of records, each with `id` (integer) and `name` (text). Names are unique.
- `sales`: a list of records, each with `product_id` (integer) and `units` (integer, 1 or more).

**Output**
- A list of (name, total units) pairs for every product that has at least one sale, sorted by total units from
  highest to lowest.

**Edge cases**
- Sales whose `product_id` matches no product are ignored.
- Products with equal totals keep their order in `products`.
