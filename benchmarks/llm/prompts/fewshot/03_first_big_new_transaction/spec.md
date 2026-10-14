# First big new transaction

**Inputs**
- `transactions`: a list of records, each with `id` (integer) and `amount` (integer).
- `limit`: an integer.

**Output**
- The `id` of the first transaction, in list order, that is not a repeat of an earlier transaction's `id` and whose
  `amount` is greater than `limit`; none (null) if there is no such transaction.

**Edge cases**
- A repeated `id` is skipped even if its amount is large; only the first transaction with each `id` counts.
