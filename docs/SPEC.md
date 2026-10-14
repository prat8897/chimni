# Chimni language reference (v0.1)

Chimni is a 2D dataflow language. **Layout is grammar**: right means "consumes the cell on my left", a new row is an
independent chain, and a column is a stage.

```text
-- comment (a whole line, or from a bare `--` cell to the end of the line)
$name[in1,in2]{out1,(a,b),out3|none}      <- signature (name is optional)
cell  cell  cell  ...                     <- row 1
cell  cell  ...                           <- row 2
```

Run: `chimni file.chimni '{"in1": ...}' [--trace] [--json]` · Check only: `chimni file.chimni` ·
Python: `chimni.load("f.chimni")(in1, in2)`

## Program structure

- The **first non-blank line** is the signature. Everything after it is rows of cells.
- Cells are separated by whitespace. Brackets `()[]{}` and `"quotes"` protect spaces inside a cell.
- **Column = cell position** in its row. Alignment with spaces is a convention for readers; position is what counts.
- Blank lines and comments are ignored. **Ties count rows, not lines.**
- Each row that ends in `^` fills the next output slot of the signature, top to bottom. The number of `^` must equal
  the number of slots (checked before running).
- One output slot returns the value itself; several return a tuple.

### Signature

| Part | Meaning |
|---|---|
| `[a,b]` | named inputs |
| `{name}` | an output |
| `{(a,b)}` | a list of pairs/records with these field names; arity is enforced (exactly 2 fields) |
| `{name\|none}` | the output may be none; without `\|none`, a none result is an error |

## Data model

- A **stream** is a list. A **scalar** is a number or string. A **record** is a dict.
- **Aggregates** (`+s +n +a +r`) produce records with a *value field* named `total`, `count`, `avg`, `run`
  (override with `:name`, e.g. `+s(amount):spend`). Stages written without a `(field)` use the value field:
  `?>[x]`, `~\`, `+s`.
- `#(k)` produces *groups*, which must be aggregated before any other cell touches them. The key field is named `k`
  (or `key` for `#()`).
- **none** passes through every cell unchanged, so `+m` on an empty stream followed by `*(name)` is simply none.

## Cells

| Cell | Meaning |
|---|---|
| `.` | empty cell. Passes its left neighbour's output through (at column 1 there is nothing to pass) |
| `@x` | start a row from input `x` |
| `@x(theirs=mine)` | inner-join input `x` into the stream where `x.theirs == item.mine`. On a name clash the stream side wins |
| `#(k)` / `#()` | group by field `k` / by the item itself |
| `%(k)` / `%()` | keep the first item per key. **Stateful** |
| `?(f)op[v]` / `?op[v]` | keep items where field `f` (or the value) `op` `v`. Ops: `> < >= <= = !=`. `v` is a number, `"text"`, or an input name |
| `?op[t:label, ..., _:label]` | **ladder**: map each item to the label of the first rung whose comparison holds; `_` is the default |
| `*(f)` / `*(a,b)` | pick one field, or several (as tuples) |
| `_l` `_u` | lowercase / uppercase, for a string or a stream of strings |
| `;w` | split into words (flattens a stream of strings) |
| `+s` `+n` `+a` | sum / count / average. Optional `(f)` and `:name` |
| `+m(f)` `+i(f)` | the **item** with the largest / smallest `f` (first wins ties). On groups: one item per group |
| `+r(f)` | running total: records `{i, run}` where `i` is the 0-based position |
| `~/` `~\` + optional `(f)` | sort ascending / descending (stable) |
| `^` | emit the left output |
| `^[n]` | emit the first `n` items as a list. **Literal `[1]`** emits the single item (or none) |
| `^[n](f)` | …then pick field `f` |
| `'` `''` `'''` | **tie**: the output of the cell 1 / 2 / 3 rows up, in this same column |
| `''/'`, `'*2`, `'+'` | arithmetic over ties, numbers and inputs. `* /` bind tighter than `+ -` |

### Arithmetic

Operands may be streams, records or scalars. A record's *value field* is what gets computed on, and the result stays in
that record. A scalar broadcasts across a stream. Two streams must be the same length and combine item by item:

- two streams of **aggregate records** (from `#(k) +s(..)` and friends) pair up **by key**, in the left stream's order,
  so two grouped rows line up even if their groups came out in a different order. Different keys, or keys under
  different field names, are a run error;
- any other two streams pair up **by position**.

Division by zero is a run error.

## Execution model

- Rows execute top to bottom. A row only depends on another row through a tie, so rows without ties between them are
  independent by construction.
- Evaluation is **eager** in v0.1: each cell finishes before the next begins. Results match what lazy evaluation would
  give; `^[1]` just doesn't stop early yet.
- Stages never mutate their input.

## Errors

**Grammar errors** (before running): a cell with nothing on its left · `^` with nothing to emit · cells after `^` ·
ties that reach above row 1 or onto an empty cell · unknown symbol, input name, or name in `[ ]` ·
number of `^` ≠ number of output slots · missing signature.

**Run errors** (with row and column): missing field (lists the ones that exist) · wrong shape for a cell ·
un-aggregated groups · output arity mismatch · none where the signature has no `|none` · division by zero ·
missing or unknown inputs.

## Decisions worth knowing about

1. `+m` returns the whole item, not the maximum value. Use `+m(f) *(f)` for the value.
2. `^[1]` emits one item, but `^[n]` always emits a list, even if the input `n` happens to be 1.
3. Tuple outputs rename fields **positionally** and require exact arity.
4. Join name clashes: the stream side wins.
5. Ladders use whatever comparison you write: `>=` means "at least", `>` is strict.
6. A row always starts with `@x` or a tie, so ladders need a source: `@score ?>=[90:A, 75:B, _:C] ^`.
