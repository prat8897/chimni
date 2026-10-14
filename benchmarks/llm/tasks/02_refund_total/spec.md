# Total refunded

Add up all refunds.

**Inputs**
- `transactions`: a list of records, each with `type` (one of the texts `"sale"`, `"refund"`, `"fee"`) and
  `amount` (integer).

**Output**
- An integer: the sum of `amount` over transactions whose `type` is exactly `"refund"`.

**Edge cases**
- No refunds (or no transactions) gives 0.
