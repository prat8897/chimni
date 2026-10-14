# Flag refunds or large amounts

Flag transactions that need review.

**Inputs**
- `transactions`: a list of records, each with `id` (integer), `type` (one of `"sale"`, `"refund"`) and
  `amount` (integer).
- `limit`: an integer.

**Output**
- A list of integers: the `id` of every transaction that is a refund **or** has an `amount` greater than `limit`
  (or both), in list order. Each transaction appears at most once.
