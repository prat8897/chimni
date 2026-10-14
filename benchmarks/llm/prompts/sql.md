## How solutions are run

Write exactly one SQLite statement (SQLite 3.x; window functions are available). Put it in a ```sql block.
- Every list input is a table with the same name. A list of records becomes a table with one column per field. A list
  of plain values becomes a table with a single column named `value`. Rows are inserted in list order, so ordering by
  `rowid` gives the original list order.
- Every other input is a bound parameter: write `:name`.
- How the answer is read from your result is stated with each task ("SQL result").
