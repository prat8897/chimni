"""Turn results/attempts.jsonl into results/REPORT.md.

    python -m benchmarks.llm.report            # results/  -> results/REPORT.md
    python -m benchmarks.llm.report --dry-run  # results/dryrun/ -> results/dryrun/REPORT.md

Statistics (as pre-registered in PREREGISTRATION.md):
  - pass@k uses the unbiased estimator 1 - C(n-c, k) / C(n, k) over the n samples of a (task, condition, model),
    then the mean over tasks. Only first attempts count for pass@k.
  - repair@3 is the share of samples that pass within the first attempt plus two repairs.
  - 95% confidence intervals: percentile bootstrap over tasks (10,000 resamples, seed 0). Differences between
    conditions are paired by task.
"""
import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from math import comb

from .common import CONDITIONS, RESULTS_DIR, load_invalid, load_tasks
from .score import CATEGORIES

B = 10_000
MARGIN = 10.0     # H1 non-inferiority margin, percentage points


# ------------------------------------------------------------------ stats
def pass_at_k(n, c, k):
    if n < k:
        return None
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def bootstrap(values, stat=statistics.fmean, b=B, seed=0):
    values = [v for v in values if v is not None]
    if not values:
        return None, None, None
    rng = random.Random(seed)
    k = len(values)
    reps = sorted(stat([values[rng.randrange(k)] for _ in range(k)]) for _ in range(b))
    return stat(values), reps[int(0.025 * b)], reps[int(0.975 * b) - 1]


def bootstrap_ratio(pairs, b=B, seed=0):
    """pairs: [(numerator, denominator)] per task; statistic = sum(num) / sum(den)."""
    pairs = [p for p in pairs if p is not None]
    if not pairs or sum(d for _, d in pairs) == 0:
        return None, None, None
    rng = random.Random(seed)
    k = len(pairs)

    def ratio(sample):
        den = sum(d for _, d in sample)
        return sum(n for n, _ in sample) / den if den else float("inf")
    reps = sorted(ratio([pairs[rng.randrange(k)] for _ in range(k)]) for _ in range(b))
    return ratio(pairs), reps[int(0.025 * b)], reps[int(0.975 * b) - 1]


def pct(x):
    return "–" if x is None else f"{100 * x:.1f}"


def ci(t, scale=100, fmt="{:.1f}"):
    v, lo, hi = t
    if v is None:
        return "–"
    return f"{fmt.format(scale * v)} [{fmt.format(scale * lo)}, {fmt.format(scale * hi)}]"


# ------------------------------------------------------------------- data
class Results:
    def __init__(self, rows, tasks, invalid):
        self.rows = rows
        self.tasks = {t.id: t for t in tasks}
        self.invalid = invalid
        chains = defaultdict(list)
        for r in rows:
            chains[(r["model"], r["condition"], r["task"], r["sample"])].append(r)
        for v in chains.values():
            v.sort(key=lambda r: r["attempt"])
        # chains whose first attempt never got an answer (API error) are dropped and counted
        self.api_errors = sum(1 for v in chains.values() if v[0]["category"] == "api_error")
        self.chains = {k: v for k, v in chains.items() if v[0]["category"] != "api_error"}
        self.models = sorted({k[0] for k in self.chains})
        self.conditions = [c for c in CONDITIONS if any(k[1] == c for k in self.chains)]

    def common_tasks(self, include_invalid=False):
        """Expressible in Chimni and available in every condition that ran: the like-for-like set."""
        return [t for t in self.tasks.values() if t.expressible and all(t.has(c) for c in self.conditions)
                and (include_invalid or t.id not in self.invalid)]

    def task_chains(self, model, cond, task_id):
        return [v for (m, c, t, _), v in self.chains.items() if m == model and c == cond and t == task_id]

    def per_task(self, model, cond, tasks, metric):
        out = {}
        for t in tasks:
            ch = self.task_chains(model, cond, t.id)
            if not ch:
                continue
            n, c = len(ch), sum(v[0]["passed"] for v in ch)
            if metric == "pass@1":
                out[t.id] = pass_at_k(n, c, 1)
            elif metric == "pass@3":
                out[t.id] = pass_at_k(n, c, 3)
            elif metric == "repair@3":
                out[t.id] = sum(any(a["passed"] for a in v[:3]) for v in ch) / n
        return out


# ----------------------------------------------------------------- report
def build(res, meta):
    L = []
    w = L.append
    dry = meta.get("mode") == "dry-run"
    w("# Chimni LLM benchmark: results\n")
    if dry:
        w("> **DRY RUN.** These numbers come from a mock model that returns reference solutions or deliberately broken "
          "ones at fixed rates. They test the pipeline and say nothing about any real model or language.\n")
    w(f"Run: {meta.get('started')} → {meta.get('finished')} · commit `{(meta.get('git_commit') or '')[:10]}` · "
      f"{meta.get('samples')} samples per (task, condition, model) · up to {meta.get('repair_attempts', 0) + 1} attempts per "
      f"sample · max_tokens {meta.get('max_tokens')}.")
    models_desc = ", ".join(f"`{m['id']}` (temperature {m.get('temperature') or 'default'}, effort "
                            f"{m.get('effort') or 'default'})" for m in meta.get("models", []))
    w(f"Models: {models_desc}.")
    spent = f"${meta.get('spent_usd', 0):.2f}" + (" (simulated)" if dry else "")
    limit = f"of a ${meta['max_cost_usd']:.2f} limit" if meta.get("max_cost_usd") is not None else "with no cost limit"
    w(f"Spent {spent} {limit}"
      + (" — **the run was stopped by the cost limit, so some samples are missing.**" if meta.get("budget_stop") else ".") + "\n")
    iso = Counter(r.get("network_isolation") for r in res.rows if r.get("network_isolation"))
    if iso:
        w("Sandbox network isolation: " + ", ".join(f"{k} ({v} attempts)" for k, v in iso.items())
          + (". **Some generated code ran without network isolation.**" if "none" in iso else ".") + "\n")
    if res.api_errors:
        w(f"{res.api_errors} samples got no reply because of API errors and are excluded.\n")
    if res.invalid:
        w("Tasks marked invalid (excluded from the headline, included in the 'with invalid' table): "
          + "; ".join(f"`{t}`: {why}" for t, why in res.invalid.items()) + "\n")

    common = res.common_tasks()
    w(f"## Headline: {len(common)} tasks every condition can attempt\n")
    w("Tasks that Chimni can express and that have a natural SQL and pandas form, so all conditions answer the same "
      "questions. pass@1 and pass@3 are from independent samples (first attempts only); repair@3 allows two repairs "
      "with the error fed back. Values are percentages with 95% bootstrap confidence intervals over tasks.\n")
    headline_table(res, common, w)

    w("\n## Chimni compared with each alternative (paired by task)\n")
    w("Difference in pass@1, Chimni minus the other condition, in percentage points. Negative means Chimni is worse.\n")
    w("| model | vs | Chimni − other, pass@1 | Chimni − other, repair@3 |")
    w("|---|---|---:|---:|")
    diffs = {}
    for m in res.models:
        for other in [c for c in res.conditions if c != "chimni"]:
            d1 = paired_diff(res, m, other, common, "pass@1")
            d3 = paired_diff(res, m, other, common, "repair@3")
            diffs[(m, other)] = d1
            w(f"| {m} | {other} | {ci(d1)} | {ci(d3)} |")

    w("\n## By difficulty (pass@1, headline task set)\n")
    diffs_by = sorted({t.difficulty for t in common}, key=["easy", "medium", "hard"].index)
    w("| model | condition | " + " | ".join(f"{d} (n={sum(t.difficulty == d for t in common)})" for d in diffs_by) + " |")
    w("|---|---|" + "---:|" * len(diffs_by))
    for m in res.models:
        for c in res.conditions:
            cells = []
            for d in diffs_by:
                vals = res.per_task(m, c, [t for t in common if t.difficulty == d], "pass@1")
                cells.append(ci(bootstrap(list(vals.values()))))
            w(f"| {m} | {c} | " + " | ".join(cells) + " |")

    w("\n## How first attempts fail\n")
    w("Share of first attempts in each category, over every task the condition can attempt (for Chimni: the "
      "expressible ones). *static* means rejected before running: a Python SyntaxError, a Chimni grammar error, or "
      "SQL that SQLite would not compile.\n")
    cats = [c for c in CATEGORIES if c != "declined"] + ["declined"]
    w("| model | condition | n | " + " | ".join(cats) + " |")
    w("|---|---|---:|" + "---:|" * len(cats))
    for m in res.models:
        for c in res.conditions:
            firsts = [v[0] for (mm, cc, t, _), v in res.chains.items() if mm == m and cc == c
                      and (c != "chimni" or res.tasks[t].expressible) and t not in res.invalid]
            cnt = Counter(r["category"] for r in firsts)
            w(f"| {m} | {c} | {len(firsts)} | " + " | ".join(
                f"{100 * cnt[k] / len(firsts):.0f}%" if firsts else "–" for k in cats) + " |")

    token_section(res, common, meta, w)
    hypotheses(res, common, diffs, w, meta)
    inexpressible_section(res, w)
    all_tasks_section(res, w)
    if res.invalid:
        w("\n## Headline including invalid tasks\n")
        headline_table(res, res.common_tasks(include_invalid=True), w)
    worst_section(res, w)
    return "\n".join(L) + "\n"


def headline_table(res, tasks, w):
    w("| model | condition | pass@1 | pass@3 | repair@3 |")
    w("|---|---|---:|---:|---:|")
    for m in res.models:
        for c in res.conditions:
            cells = [ci(bootstrap(list(res.per_task(m, c, tasks, k).values()))) for k in ("pass@1", "pass@3", "repair@3")]
            w(f"| {m} | {c} | " + " | ".join(cells) + " |")


def paired_diff(res, model, other, tasks, metric):
    a = res.per_task(model, "chimni", tasks, metric)
    b = res.per_task(model, other, tasks, metric)
    return bootstrap([a[t] - b[t] for t in a if t in b and a[t] is not None and b[t] is not None])


def code_token_measure(res):
    has_anthropic = any(r.get("code_tokens") and "anthropic" in r["code_tokens"] for r in res.rows)
    return "anthropic" if has_anthropic else "o200k_base"


def token_section(res, common, meta, w):
    w("\n## Tokens\n")
    pt = meta.get("prompt_tokens") or {}
    if pt:
        keys = sorted({k for row in pt.values() for k in row})
        w("**System prompt size per condition** (documentation, conventions and few-shot examples; sent with every "
          "request, cached after the first):\n")
        w("| condition | " + " | ".join(keys) + " |")
        w("|---|" + "---:|" * len(keys))
        for c, row in pt.items():
            w(f"| {c} | " + " | ".join(str(row.get(k, "–")) for k in keys) + " |")
        w("")
    measure = code_token_measure(res)
    w(f"**Generated code per correct solution** (headline tasks; any passing attempt). Tokens counted with "
      f"`{measure}`{' (Anthropic count_tokens)' if measure == 'anthropic' else ' (tiktoken; no Anthropic counts in this run)'}; "
      "characters for reference. Mean of per-task means.\n")
    w("| model | condition | tasks with a correct solution | tokens | cl100k | o200k | chars |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for m in res.models:
        for c in res.conditions:
            per = code_stats(res, m, c, common)
            if not per:
                w(f"| {m} | {c} | 0 | – | – | – | – |")
                continue

            def mean_of(key):
                vals = [v[key] for v in per.values() if v.get(key) is not None]
                return f"{statistics.fmean(vals):.0f}" if vals else "–"
            w(f"| {m} | {c} | {len(per)} | {mean_of(measure)} | {mean_of('cl100k_base')} | {mean_of('o200k_base')} | "
              f"{mean_of('chars')} |")
    w("\n**Total cost per correct solution** (headline tasks): every billed token (system prompt, task, replies "
      "including thinking, and all repair attempts) divided by the number of samples that ended correct within three "
      "attempts.\n")
    w("| model | condition | samples | correct | billed tokens / correct | USD / correct |")
    w("|---|---|---:|---:|---:|---:|")
    for m in res.models:
        for c in res.conditions:
            tok, usd, n, ok = total_cost(res, m, c, common)
            w(f"| {m} | {c} | {n} | {ok} | {f'{tok / ok:,.0f}' if ok else '–'} | {f'{usd / ok:.4f}' if ok else '–'} |")


def code_stats(res, model, cond, tasks):
    out = {}
    for t in tasks:
        ok = [a for v in res.task_chains(model, cond, t.id) for a in v if a["passed"]]
        if not ok:
            continue
        row = {"chars": statistics.fmean(a["code_chars"] for a in ok)}
        for key in ("anthropic", "cl100k_base", "o200k_base"):
            vals = [a["code_tokens"][key] for a in ok if a.get("code_tokens") and key in a["code_tokens"]]
            row[key] = statistics.fmean(vals) if vals else None
        out[t.id] = row
    return out


def billed_tokens(a):
    u = a.get("usage") or {}
    return sum(u.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                                     "cache_read_input_tokens"))


def total_cost(res, model, cond, tasks, per_task=False):
    rows = {}
    for t in tasks:
        ch = res.task_chains(model, cond, t.id)
        tok = sum(billed_tokens(a) for v in ch for a in v)
        usd = sum(a.get("billed_cost_usd", 0) for v in ch for a in v)
        ok = sum(any(a["passed"] for a in v) for v in ch)
        rows[t.id] = (tok, usd, len(ch), ok)
    if per_task:
        return rows
    return tuple(sum(r[i] for r in rows.values()) for i in range(4))


def hypotheses(res, common, diffs, w, meta):
    w("\n## Pre-registered hypotheses\n")
    w("Verdicts are computed mechanically from the decision rules in PREREGISTRATION.md.\n")
    w("| | hypothesis | model | estimate [95% CI] | verdict |")
    w("|---|---|---|---|---|")
    measure = code_token_measure(res)
    for m in res.models:
        d = diffs.get((m, "python"))
        if d and d[0] is not None:
            v = ("supported" if d[1] > -MARGIN / 100 else "refuted" if d[2] < -MARGIN / 100 else "inconclusive")
            w(f"| H1 | Chimni pass@1 is no more than {MARGIN:.0f} points below Python | {m} | {ci(d)} points | {v} |")
        a = code_stats(res, m, "chimni", common)
        b = code_stats(res, m, "python", common)
        both = [t for t in a if t in b and a[t].get(measure) is not None and b[t].get(measure) is not None]
        dd = bootstrap([a[t][measure] - b[t][measure] for t in both])
        if dd[0] is not None:
            v = "supported" if dd[2] < 0 else "refuted" if dd[1] > 0 else "inconclusive"
            w(f"| H2 | Chimni needs fewer code tokens per correct solution than Python ({measure}) | {m} | "
              f"{ci(dd, scale=1)} tokens (n={len(both)} tasks) | {v} |")
        rc = total_cost(res, m, "chimni", common, per_task=True)
        rp = total_cost(res, m, "python", common, per_task=True)
        shared = [t for t in rc if t in rp]
        # ratio of (Chimni tokens per correct) to (Python tokens per correct), bootstrapped over tasks
        rng = random.Random(0)

        def ratio(ts):
            ok_c, ok_p = sum(rc[t][3] for t in ts), sum(rp[t][3] for t in ts)
            if not ok_c or not ok_p:
                return None
            return (sum(rc[t][0] for t in ts) / ok_c) / (sum(rp[t][0] for t in ts) / ok_p)
        point = ratio(shared)
        if point is not None:
            reps = sorted(x for x in (ratio([shared[rng.randrange(len(shared))] for _ in shared]) for _ in range(B))
                          if x is not None)
            lo, hi = reps[int(0.025 * len(reps))], reps[int(0.975 * len(reps)) - 1]
            v = "supported" if lo > 1 else "refuted" if hi < 1 else "inconclusive"
            w(f"| H3 | Counting the documentation, Chimni costs more billed tokens per correct solution than Python | "
              f"{m} | ratio {point:.2f} [{lo:.2f}, {hi:.2f}] | {v} |")
    w("")
    for m in res.models:
        d = diffs.get((m, "python"))
        if d and d[0] is not None:
            direction = "lower" if d[0] < 0 else "higher"
            w(f"- **{m}:** Chimni's pass@1 was {abs(100 * d[0]):.1f} points {direction} than Python's "
              f"(95% CI {100 * d[1]:+.1f} to {100 * d[2]:+.1f}).")


def inexpressible_section(res, w):
    tasks = [t for t in res.tasks.values() if not t.expressible]
    if not tasks:
        return
    w("\n## Tasks Chimni cannot express (reported separately)\n")
    w("These are not counted as Chimni failures. The Chimni prompt allows answering CANNOT_EXPRESS. A *pass* here "
      "would mean the task is expressible after all and should be re-classified.\n")
    w("| task | model | Chimni: declined | Chimni: wrote code that failed | Chimni: passed | python pass@1 | pandas pass@1 | sql pass@1 |")
    w("|---|---|---:|---:|---:|---:|---:|---:|")
    for t in tasks:
        for m in res.models:
            firsts = [v[0] for v in res.task_chains(m, "chimni", t.id)]
            n = len(firsts) or 1
            dec = sum(r["category"] == "declined" for r in firsts)
            ok = sum(r["passed"] for r in firsts)
            others = []
            for c in ("python", "pandas", "sql"):
                v = res.per_task(m, c, [t], "pass@1").get(t.id)
                others.append(pct(v))
            w(f"| `{t.id}` | {m} | {100 * dec / n:.0f}% | {100 * (len(firsts) - dec - ok) / n:.0f}% | "
              f"{100 * ok / n:.0f}% | " + " | ".join(others) + " |")


def all_tasks_section(res, w):
    w("\n## Every task, pass@1 by condition\n")
    w("| task | difficulty | " + " | ".join(f"{m} {c}" for m in res.models for c in res.conditions) + " |")
    w("|---|---|" + "---:|" * (len(res.models) * len(res.conditions)))
    for t in sorted(res.tasks.values(), key=lambda t: t.id):
        cells = []
        for m in res.models:
            for c in res.conditions:
                if not t.has(c) or (c == "chimni" and not t.expressible):
                    cells.append("n/a")
                else:
                    cells.append(pct(res.per_task(m, c, [t], "pass@1").get(t.id)))
        flag = " (invalid)" if t.id in res.invalid else "" if t.expressible else " (inexpressible)"
        w(f"| `{t.id}`{flag} | {t.difficulty} | " + " | ".join(cells) + " |")


def worst_section(res, w):
    w("\n## Where Chimni failed most\n")
    for m in res.models:
        rates = []
        for t in res.tasks.values():
            if not t.expressible or t.id in res.invalid:
                continue
            firsts = [v[0] for v in res.task_chains(m, "chimni", t.id)]
            if firsts:
                rates.append((sum(not r["passed"] for r in firsts) / len(firsts), t.id, firsts))
        rates.sort(key=lambda x: (-x[0], x[1]))
        shown = [r for r in rates if r[0] > 0][:5]
        w(f"### {m}\n")
        if not shown:
            w("Chimni passed every expressible task on the first attempt in every sample.\n")
            continue
        for rate, tid, firsts in shown:
            fails = [r for r in firsts if not r["passed"]]
            top = Counter(r["category"] for r in fails).most_common(1)[0][0]
            ex = next(r for r in fails if r["category"] == top)
            w(f"**`{tid}`**: failed {100 * rate:.0f}% of first attempts; most often *{top}*. Example:\n")
            w("```chimni\n" + (ex.get("code") or ex.get("response") or "").strip()[:1500] + "\n```\n")
            w(f"Result: {ex.get('message') or top}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m benchmarks.llm.report")
    ap.add_argument("--dry-run", action="store_true", help="report on results/dryrun/")
    ap.add_argument("--dir", help="results directory")
    args = ap.parse_args(argv)
    d = RESULTS_DIR / "dryrun" if args.dry_run else (RESULTS_DIR if not args.dir else __import__("pathlib").Path(args.dir))
    rows = [json.loads(line) for line in (d / "attempts.jsonl").read_text(encoding="utf-8").splitlines() if line]
    meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
    res = Results(rows, load_tasks(), load_invalid())
    (d / "REPORT.md").write_text(build(res, meta), encoding="utf-8")
    print(f"wrote {d / 'REPORT.md'}")


if __name__ == "__main__":
    main()
