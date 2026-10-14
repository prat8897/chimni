# First n sign-ups

List the names of the earliest sign-ups.

**Inputs**
- `users`: a list of records, each with `name` (text) and `joined` (integer day number). The list is already in
  sign-up order.
- `n`: an integer, 0 or more.

**Output**
- A list of texts: the `name` of the first `n` users, in list order.

**Edge cases**
- If there are fewer than `n` users, return all their names. The result is always a list, even when `n` is 1.
