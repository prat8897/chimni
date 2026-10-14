# Pre-registration: can an LLM write Chimni as reliably as Python, pandas or SQL?

**Status:** written and committed before any real model call. No model other than the deterministic mock in
`providers.py` has seen any task. After this document and the tasks are reviewed, the task files and prompts will be
hashed into `FROZEN.json` (`python -m benchmarks.llm.run --freeze`). The runner refuses to make real calls if anything
has changed since then.

## Question

Given the same plain-English specification, does a model write a **correct** Chimni program as often as it writes a
correct Python, pandas or SQL solution, and what does each correct solution cost in tokens once Chimni's
documentation is counted?

## Hypotheses

Each hypothesis is evaluated separately for each model. There is no correction for multiple comparisons; the report
gives every estimate with its confidence interval, so readers can judge for themselves.

| | Hypothesis | Measure | Decision rule |
|---|---|---|---|
| **H1** | Chimni's pass@1 is within 10 percentage points of Python's (non-inferiority). | Mean over headline tasks of per-task (pass@1 Chimni − pass@1 Python), paired by task. | **Supported** if the 95% CI's lower bound is above −10 points; **refuted** if the upper bound is below −10; otherwise **inconclusive**. |
| **H2** | A correct Chimni solution is shorter in tokens than a correct Python solution. | Per task, the mean token count of the generated code over correct attempts; then the mean over tasks where both conditions have a correct solution of (Chimni − Python). Primary tokenizer: Anthropic `count_tokens` for the model that wrote the code. Secondary: tiktoken `o200k_base` and `cl100k_base`. | **Supported** if the 95% CI's upper bound is below 0; **refuted** if the lower bound is above 0; otherwise **inconclusive**. |
| **H3** | Once documentation is counted, Chimni costs **more** total tokens per correct solution than Python. | (All billed tokens for Chimni ÷ Chimni samples correct within 3 attempts) ÷ (the same for Python), over headline tasks. Billed tokens include system prompt, task, reply (thinking included) and every repair. | **Supported** if the 95% CI of the ratio is entirely above 1; **refuted** if entirely below 1; otherwise **inconclusive**. |

H1 and H2 come from the project's stated motivation. H3 is our own prediction: the Chimni system prompt is about 2.5×
the size of Python's (about 4.7k vs 1.9k tokens), and we expect that to outweigh shorter code.

**Exploratory, no prediction:** Chimni vs pandas and vs SQL on pass@1 and repair@3; whether error feedback helps
Chimni more than the others (Chimni errors name a row and column); which failure categories dominate per condition;
how often models answer CANNOT_EXPRESS on the four inexpressible tasks, and how often they wrongly decline
expressible ones.

## Task set

30 tasks in `tasks/`, written for this benchmark. None of the ten repository examples is used as a test task: they
appear in the documentation and are used as few-shot examples instead. Each task has a spec, a trusted Python
reference, a seeded input generator, hand-written edge cases (empty input, ties, boundaries, none), and pandas and
SQL references. All four references agree on every test input (`tests/test_tasks.py`).

Difficulty: 9 easy, 13 medium, 8 hard. Four tasks are **inexpressible in Chimni by design** and are reported
separately, never counted as Chimni failures. The **headline set** is the 26 expressible tasks, all of which have
natural pandas and SQL forms, so every condition answers the same questions.

| Task | Difficulty | Chimni can express | Other conditions | Chimni features |
|---|---|---|---|---|
| `01_count_in_stock` | easy | yes | pandas, sql | filter; count |
| `02_refund_total` | easy | yes | pandas, sql | filter on text; sum |
| `03_cheapest_product` | easy | yes | pandas, sql | min item; pick; none |
| `04_unique_tags_sorted` | easy | yes | pandas, sql | lowercase; dedupe; sort |
| `05_daily_changes` | easy | **no** | pandas, sql | positional offset |
| `06_average_rating` | easy | yes | pandas, sql | average; none |
| `07_highest_reading` | easy | yes | pandas, sql | max of plain numbers; none |
| `08_first_n_signups` | easy | yes | pandas, sql | take n; pick |
| `09_orders_per_customer` | medium | yes | pandas, sql | group; count; sort desc |
| `10_team_averages` | medium | yes | pandas, sql | group; average |
| `11_distinct_visitors` | medium | yes | pandas, sql | dedupe; count |
| `12_busy_days` | medium | yes | pandas, sql | group; count; filter on aggregate; pick |
| `13_units_sold_by_product` | medium | yes | pandas, sql | join; group; sum; sort desc |
| `14_lowest_balance` | medium | yes | pandas, sql | running total; min item; none |
| `15_grades_with_cutoffs` | medium | yes | pandas, sql | ladder with input thresholds |
| `16_price_range` | medium | yes | pandas, sql | max item; min item; tie arithmetic; none |
| `17_top_categories` | medium | yes | pandas, sql | group; count; sort desc; take n |
| `18_normalized_scores` | medium | yes | pandas, sql | max; tie broadcast; division |
| `19_priciest_per_category` | medium | yes | pandas, sql | group; max item per group; multi-pick |
| `20_inventory_value` | hard | yes | pandas, sql | pick; positional stream arithmetic; sum |
| `21_revenue_per_unit_by_category` | hard | yes | pandas, sql | group; two grouped rows; positional division |
| `22_leaderboard` | hard | yes | pandas, sql | two-key sort (stable sort twice); multi-pick |
| `23_deviation_from_mean` | hard | yes | pandas, sql | average; tie broadcast; subtraction |
| `24_top_customer_share` | hard | yes | pandas, sql | group; sum; max item; three-row tie; none |
| `25_grade_band_counts` | hard | yes | pandas, sql | ladder; group by value; count |
| `26_loyal_customer_names` | hard | yes | pandas, sql | join; group; sum; filter on aggregate; pick; sort |
| `27_customers_without_orders` | medium | **no** | pandas, sql | anti-join |
| `28_median_time` | medium | **no** | pandas, sql | median |
| `29_flagged_transactions` | easy | **no** | pandas, sql | OR filter |
| `30_second_highest_score` | hard | yes | pandas, sql | max; four-row tie; filter; none |

One change was made to the approved plan before freezing: `second_highest_score` was found to be expressible (see
FINDINGS.md #2) and moved to the expressible set. `daily_changes` replaced `word_count` as an inexpressible task.

## Conditions

Every condition gets the same spec text, the same conventions (`prompts/contract.md`), a short "how solutions are
run" section, and few-shot pairs (spec → solution) built from the ten repository examples.

| Condition | Extra documentation | Few-shots | Output |
|---|---|---|---|
| chimni | `docs/SPEC.md` + `docs/TUTORIAL.md` | 10 | a Chimni program; may answer CANNOT_EXPRESS |
| python | none | 10 | `def solve(...)`, standard library only |
| pandas | none | 10 | `def solve(...)` using pandas |
| sql | none | 8 (02 and 05 have no single-statement SQL form) | one SQLite statement |

The documentation budget is **not** padded to be equal. Models already know Python, pandas and SQL; they do not know
Chimni. That documentation is a real cost of using Chimni, so the report states each system prompt's size and H3
counts it.

## Models and sampling

From `models.yaml`: `claude-sonnet-5-5` and `claude-haiku-5-5` (enabled); `claude-opus-5-5` is configured but off by
default because of cost. Default effort for each model, recorded in the results. Thinking is on by default on these
models and its tokens are billed as output; they are counted.

- **n = 5 samples** per (task, condition, model), each a fresh request with no shared context.
- Up to **2 repairs** per sample after a failure (3 attempts in total).
- `max_tokens` 16,000 per reply. Refusal fallbacks to other models are **off**, so every answer comes from the named
  model.

## Scoring

Each attempt's code is extracted from the first fenced block tagged with the condition's language (or the first block
of any kind). It runs in a sandboxed subprocess (`sandbox.py`: temp directory, `python -I`, CPU/file/process limits,
no network where the OS allows, 30 s for the whole batch) on 300 seeded random inputs plus the task's hand-written
edge cases. Outputs are compared with the Python reference after converting tuples to lists, with a numeric
tolerance of 1e-9.

Every attempt gets one category: *pass*, *wrong_output*, *runtime*, *static* (rejected before running: SyntaxError,
Chimni grammar error, SQL that SQLite will not compile), *timeout*, *extraction* (no code block) or *declined*
(CANNOT_EXPRESS, Chimni only).

**Repair feedback.** For static and runtime errors the error message is sent back. For a wrong output, the input,
expected and actual output are shown **only if the failing input is a hand-written edge case**; for a random input the
model is only told "wrong result on a hidden test input". Random test inputs are never shown.

## Metrics and analysis

- **pass@1, pass@3:** the unbiased estimator 1 − C(n−c, k)/C(n, k) over the 5 first-attempt samples per task, then
  the mean over tasks.
- **repair@3:** the share of samples correct within the first attempt plus two repairs.
- **95% confidence intervals:** percentile bootstrap over tasks, 10,000 resamples, seed 0; comparisons are paired by
  task.
- Breakdowns by difficulty, failure category, token cost (code tokens per correct solution; billed tokens and USD per
  correct solution), the inexpressible tasks, and the tasks where Chimni failed most, with code and error.
- Samples with no reply (API errors) are excluded and counted. If `--max-cost` stops the run, all completed samples are
  analysed (the runner works sample by sample across all tasks, so coverage stays even) and the report says so.

## Integrity rules

1. This document, the tasks and the prompts are committed before any real call.
2. `FROZEN.json` hashes every task file, prompt file, the Chimni docs, and every rendered prompt. Real runs refuse to
   start if anything differs.
3. Tasks are not edited after results are seen. A task found to be flawed is listed in `INVALID.json` with the reason,
   and the report shows the headline both with and without it.
4. Every model reply is cached, so the raw data can be re-scored and re-analysed without new calls.

## Deviations from the original brief

| Brief | What we do | Why |
|---|---|---|
| 5 samples at temperature 0.7, plus a greedy run | 5 samples at each model's default sampling; no greedy run | Current Claude models reject non-default sampling parameters (FINDINGS.md #7). |
| "pass@3" for the repair loop | pass@3 means 3 independent samples; **repair@3** means first attempt + 2 repairs; both are reported | The two meanings differ, and both are useful. |
| 10 few-shots per condition | SQL gets 8 | Two examples have no single-statement SQL form (FINDINGS.md #8). |
| Equalize documentation budget | Not padded; sizes reported and counted in H3 | Padding Python's prompt with filler would not make the comparison fairer. |
