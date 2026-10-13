# Learn Chimni in ten minutes

You don't need to know any programming language to follow this page. If you do, you'll notice that most of the
things you usually write — loops, counters, temporary variables — simply don't exist here.

## The factory

Think of a factory with conveyor belts.

- **Each row is one belt.** Stuff goes in at the left and comes out at the right.
- **Each cell is a machine.** It does one job to whatever arrives, then passes the result to the machine on its right.
- **A new row is a different belt.** Two belts share nothing unless you connect them — so the computer knows they can
  run at the same time.
- **The top line is the label on the factory:** what goes in, and what comes out.

```text
$[users]{names}
@users  ?(age)>=[18]  *(name)  ~/  ^
```

Read it left to right, like a sentence:

1. `$[users]{names}` — the factory takes `users` and produces `names`.
2. `@users` — pick up the users.
3. `?(age)>=[18]` — only let through people whose **age** is **at least 18**.
4. `*(name)` — from each person, keep just the **name**.
5. `~/` — sort them, smallest to largest (`~\` goes the other way).
6. `^` — send the result out.

## The machines

| Machine | What it does | Example |
|---|---|---|
| `@` | pick up items from an input | `@orders` |
| `#` | sort items into piles | `#(customer)` |
| `%` | throw away repeats | `%(id)` |
| `?` | only let some items through | `?(amount)>[limit]` |
| `+s` `+n` `+a` | add up / count / average | `+s(amount)` |
| `+m` `+i` | find the biggest / smallest item | `+m(age)` |
| `*` | keep just one field | `*(name)` |
| `~/` `~\` | sort small→big / big→small | `~\(total)` |
| `^` | finish: send this out | `^[3]` sends the first three |

The brackets tell a machine what it is looking at:

- `( )` is **what to look at** — usually a field, like `(age)`.
- `[ ]` is **the setting** — a number or an input, like `[18]` or `[limit]`.

## Dots are blank spots

If one belt skips a machine, put a `.` there so everything stays lined up. A dot just passes things along.

```text
$[orders,min_total]{(customer,total),revenue}
@orders  #(customer)  +s(amount)  ?>[min_total]  ~\(total)  ^
@orders  .            +s(amount)  .              .          ^
```

Two belts, two outputs. The second belt adds up *all* the orders (the dots skip the machines it doesn't need).
Both belts end in `^`, and they fill the two output slots `{…}` in order, top to bottom.

## Connecting belts: the quote

What if one belt needs an answer from another? Use a **quote** `'` — it means *"the cell above me, in this column."*
Two quotes `''` mean two rows up.

```text
$[sales]{(cat,share)}
@sales  #(cat)  +s(amount)
@sales  .       +s(amount)
.       .       ''/'        ^
```

- Row 1 adds up sales per category.
- Row 2 adds up all sales.
- Row 3's `''/'` means: *two rows up* (per-category totals) **divided by** *one row up* (the grand total).

That's a share of the total, and there isn't a single variable name in the program.

## The "none" rule

Sometimes there's nothing to give back — the oldest user in an empty list, say. Say so in the signature:

```text
$[users]{name|none}
@users  +m(age)  *(name)  ^
```

`|none` means "this may come out empty". If you forget it and the result *is* empty, Chimni stops and tells you.

## When something goes wrong

Chimni tells you the **row and column** and what it expected:

```text
run error at row 1, col 2: no field 'v' (item has: w)
```

Add `--trace` to see what every cell produced.

## Your turn

Write a program that takes `numbers` and returns the ones above `limit`, biggest first.

<details><summary>Answer</summary>

```text
$[numbers,limit]{big}
@numbers  ?>[limit]  ~\  ^
```

`?>[limit]` has no `(field)` because the items are plain numbers — the number *is* the value.

</details>

Now write one that returns how many users are under 18.

<details><summary>Answer</summary>

```text
$[users]{minors}
@users  ?(age)<[18]  +n  ^
```

</details>

Next: the full [language reference](SPEC.md), or the [`examples/`](../examples) folder.
