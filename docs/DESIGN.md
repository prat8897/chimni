# Design notes

How Chimni got its shape, what we got wrong on the way, and what is still open. If you want to argue with the
language, this is the page to argue with.

## Where the idea came from

Sanskrit packs a lot of information into the grammar itself: case endings tell you a word's role, tense tells you
*when*. The question was whether a programming language could do the same — put **inputs, outputs and dependencies in
the grammar** instead of leaving them to be inferred from a function body.

The first sketch was four vectors per program — *input context*, *output context*, *rules*, *question* — with "AND
THEN" / "BEFORE THIS" playing the role of tense. That turned into a compact symbol notation, and then something
better: **if "depends on the previous output" is the default, then geometry can carry it.**

- Moving **right** = "consumes the output on my left."
- Starting a **new row** = "independent chain."
- A **column** = how many steps from the data's entry.
- A **tie** (`'`) = "the cell above me", which is how rows join without names.

Tense in Sanskrit is a property of the word. Dependency in Chimni is a property of where the cell sits.

## Principles

1. **Position is grammar.** Anything layout can say, names shouldn't have to.
2. **Contracts up front.** The signature declares inputs and the *shape* of each output, and the interpreter holds the
   program to it.
3. **Closed vocabulary.** Every symbol means one thing, so the language is deterministic and can be checked without
   guessing. Anything outside the vocabulary needs a new symbol or an escape hatch, deliberately.
4. **Read it, don't decode it.** A row should read left to right like a sentence.
5. **Errors name a row and a column.**

## What we got wrong, and fixed

- **"Set of customers" can't satisfy "sorted high to low."** The first output contract was a set. A set is unordered
  and drops the totals the original returned. This is the kind of bug the signature is meant to catch, and it is the
  reason tuple outputs enforce their arity.
- **`customer` and `amount` aren't inputs.** They're fields *inside* `orders`. The input list holds only what the
  caller supplies.
- **The first sketch needed something to interpret it.** The early notation was loose enough that it needed a
  person, or a model, to read meaning into it. Once every symbol had one meaning and layout carried the dependencies,
  it became an ordinary deterministic language: a plain interpreter checks and runs it.
- **The ladder example was wrong.** `?>[90:A, …]` used a strict `>` where the Python used `>=`, so a score of exactly
  90 got the wrong grade. The differential tests are there to catch this class of slip.
- **Tied grouped rows paired up by position.** `''/'` on two grouped rows divided item *i* by item *i*, so if the
  groups came out in a different order the answer was silently wrong. Aggregate records now pair up **by key**, and
  rows with different keys are an error.
- **`+m` was ambiguous.** Does it return the max *value* or the max *item*? It returns the item; `+m(f) *(f)` gives
  the value.

## Open questions

**Whitespace sensitivity.** Layout carries meaning *only through cell order*, not through the number of spaces, which
makes the language robust to re-flowing. But tools that wrap long lines or strip newlines will still change a
program's meaning, since a new line is a new row. `chimni fmt` keeps columns aligned so ties are easy to check by
eye, but it can't protect against a tool that joins lines.

**Ties are powerful but can be cryptic.** "Second-highest distinct value" takes four rows and three ties (subtract the
max, keep the negatives, take their max, add the max back). It works, but it is a puzzle to read. Is that a missing
cell, or acceptable?

**Characters with baggage.** `\` is an escape character in JSON, shells and most string literals; `'` is a quote
character almost everywhere. Both survive in the interpreter, but pasting a program into some pipelines may mangle
them. `↑`/`↓` for sort direction is one alternative; a different tie marker is another.

**Side effects.** Dataflow tells you order by data dependency. "Write to the database, then send an email" has no
data flowing between the two steps, so the layout rules call them independent. We need an explicit way to say "order
matters though nothing flows" — likely a distinct kind of cell.

**Stateful cells.** `%(k)` (dedupe) and `+r` (running total) remember things across items. That's fine in a single
stream, but it means a cell isn't always a pure function, and any future optimizer needs to know which ones aren't.

**Mutation.** Something like "add to a set only if the amount was small" isn't a clean pipeline. The boundary of the
language is: dataflow, beautifully; mutation, poorly. Either that stays the boundary, or we add an explicit state cell.

**Branching and loops.** Ladders cover `if/elif/else` that maps a value to a label. General branching (two rows that
diverge from a cell and rejoin) and early exit as control flow are not designed yet.

## Prior art

| Influence | What Chimni took |
|---|---|
| Pāṇini's *Aṣṭādhyāyī* | grammar as a compact rule system; roles marked by endings (*kāraka*) |
| APL / J / K / BQN / Uiua | dense symbols, left-to-right, tacit composition |
| jq, Unix pipes | each stage consumes the previous stage's output |
| Spreadsheets | position is meaning; cells reference other cells |
| Befunge and 2D languages | layout as control flow |
| Dataflow / flow-based programming | programs as graphs of independent transforms |

Corrections and additions welcome.
