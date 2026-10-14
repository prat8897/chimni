# Lowest balance

Find the lowest balance an account reaches.

**Inputs**
- `transactions`: a list of records, each with `amount` (integer; deposits are positive, withdrawals negative),
  in time order. The balance starts at 0.

**Output**
- An integer: the lowest balance after any transaction, or none (null) if there are no transactions.

**Edge cases**
- The starting balance of 0 does not count; only balances after a transaction do.
