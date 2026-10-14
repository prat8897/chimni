# Findings

Bugs, ambiguities and surprises found while building the benchmark. Per the benchmark's rules, the interpreter and
the language spec were **not** changed; each item says how the benchmark works around it.

## About the language

### 1. A tie between two grouped rows pairs groups by position, not by key (silent wrong answer)

`''/'` on two lists of aggregated groups divides item *i* by item *i*. It checks that the lists have the same length,
but not that item *i* on both sides has the same key. If the two rows group different inputs, or the same keys
appear in a different order, the result is wrong and nothing complains:

```text
$[sales,returns]{(category,ratio)}
@sales    #(category)  +s(revenue)
@returns  #(category)  +s(units)
.         .            ''/'          ^
```

With sales `a:10, b:100` and returns `b:1, a:10` this returns `[('a', 10.0), ('b', 10.0)]`; the right answer is
`[('a', 1.0), ('b', 100.0)]`.

*Workaround:* none needed. Tasks 21 and 24 rely on positional pairing, but both group the **same** input by the
same key, so the order is identical by construction. This is a candidate for a run-time check (keys must match) or
a keyed join between rows.

### 2. "Second-highest distinct value" turned out to be expressible

The approved plan listed `second_highest_score` as inexpressible. It isn't. Four rows and three ties do it: subtract
the maximum from every score, keep the negative differences, take their maximum, then add the maximum back.

```text
$[scores]{second|none}
@scores  .     .      .
@scores  +m    .      .
.        ''-'  ?<[0]  +m
.        .     .      '+''  ^
```

*Change made before freezing:* the task stays in the set as a **hard, expressible** task (#30). Its place among the
inexpressible tasks went to `daily_changes` (#05, consecutive differences), which replaced `word_count`. This keeps
four inexpressible tasks and removes the one task that SQL and pandas could not attempt. The ties are more powerful
than the docs suggest, but programs like this are hard to read.

### 3. A tie needs a non-empty cell to land on, so rows get padded with dots

A tie may not point at an empty cell, so a row that a later tie reads must extend to that column, padded with `.`
(row 1 and row 2 above). SPEC.md states the rule ("ties … onto an empty cell" is a grammar error), but nothing in
the docs or examples shows the padding pattern, so a model has to work it out. Tasks 16, 18, 20, 21, 23, 24 and 30
all need it. *No workaround:* this is part of what the benchmark measures.

### 4. `^[n]` and `^[1]` behave differently by design

`^[1]` emits a single item; `^[n]` emits a list even when the input `n` is 1. SPEC.md documents this. Task 08
(`first_n_signups`, `n` may be 1) checks whether models notice. Not a bug.

### 5. No interpreter bugs found

All 26 expressible reference programs agree with the Python references on 300 random inputs plus hand-written edge
cases, including empty inputs, ties, single items and none.

## About the benchmark and its tools

### 6. pandas: an inner `merge` did not keep the left table's order

`products.merge(sales, left_on="id", right_on="product_id")` (pandas 3.0.6) returned rows in an order where tied
products came out in `sales` order, not `products` order, which broke the stated tie rule. The pandas reference for
task 13 now carries the left index through the merge and sorts by it. Model-written pandas will likely hit the same
problem; that counts against pandas, as it should.

### 7. Current Claude models do not accept a sampling temperature

The brief asked for 5 samples at temperature 0.7 plus a greedy run. Claude Sonnet 5.5 and Haiku 5.5 return HTTP 400
for any non-default `temperature`, and Opus 5.5 does not accept sampling parameters at all, so neither is possible.
*Workaround:* 5 samples at each model's default sampling, and no greedy run. `models.yaml` has a per-model
`temperature` for providers that accept one. Recorded as a deviation in PREREGISTRATION.md.

### 8. SQL gets 8 few-shot examples, not 10

Example 02 has two outputs and example 05 splits text into words. Neither fits "one SQLite statement", so the SQL
prompt uses the other eight. Python, pandas and Chimni get all ten.
