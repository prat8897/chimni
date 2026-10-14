# Chimni LLM benchmark

Can a model write **correct** Chimni from a plain-English spec as reliably as it writes Python, pandas or SQL, and at
what token cost once Chimni's documentation is counted?

- **Design and hypotheses:** [PREREGISTRATION.md](PREREGISTRATION.md) (written before any real model call)
- **Things found along the way:** [FINDINGS.md](FINDINGS.md), including one silent-wrong-answer hazard in the language
- **Results:** `results/REPORT.md`, after a real run

## How it works

```
tasks/NN_name/       spec.md · reference.py (trusted) · reference.chimni · reference.sql · reference_pandas.py
                     input_gen.py (seeded) · edge_cases.json · meta.json
prompts/             contract.md (shared) · chimni.md python.md pandas.md sql.md · fewshot/ (the 10 repo examples)
run.py               builds prompts, calls models (cached), runs repair loops, enforces --max-cost
score.py             extracts code, runs it, compares with reference.py, classifies failures, writes feedback
sandbox.py/harness.py  runs generated code in a limited, network-less subprocess
report.py            results/attempts.jsonl -> results/REPORT.md
providers.py         Anthropic (official SDK) and a mock; add others here
```

For each (task, condition, model) the runner draws 5 independent samples. A failed sample gets up to two repairs,
with the error fed back. Every attempt is run on the task's edge cases plus 300 random inputs and compared with the
Python reference.

## Reproduce

From the repository root:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e . -r benchmarks/llm/requirements.txt

# 1. the benchmark's own tests (references agree, few-shots are correct, the pipeline works)
python -m unittest discover -s benchmarks/llm/tests -t .

# 2. the whole pipeline with a free mock model
python -m benchmarks.llm.run --dry-run
python -m benchmarks.llm.report --dry-run           # -> benchmarks/llm/results/dryrun/REPORT.md

# 3. a real run (after reviewing PREREGISTRATION.md and the tasks)
python -m benchmarks.llm.run --freeze               # once; commit FROZEN.json
export ANTHROPIC_API_KEY=...
python -m benchmarks.llm.run --max-cost 20          # hard stop at $20
python -m benchmarks.llm.report                     # -> benchmarks/llm/results/REPORT.md
```

`make bench-test`, `make bench-dry`, `make bench-freeze` and `make bench-run MAX_COST=20` do the same.

Useful flags: `--models haiku-5.5` · `--tasks 01,13,22` · `--conditions chimni,python` · `--samples 2` ·
`--no-repair` · `--workers 8`. Use `--help` for the rest.

**Reruns are free.** Every reply is cached in `cache/` under a hash of the full request plus the sample number, so
rerunning (say, after a scorer fix) re-scores cached replies without new calls. Delete `cache/live/` to resample.

**Cost.** The limit is enforced *before* each call: the runner reserves the worst case (the whole prompt at the cache
write rate plus `max_tokens` of output) and stops scheduling when the next call could exceed it. A full run makes
600 first attempts per model, plus repairs. Thinking-token use dominates the cost and isn't known in advance, so try a
small slice first (`--tasks 01,13 --samples 1`) and check `spent_usd` in `results/run_meta.json`. Prices are in
`models.yaml`; check them before a real run.

## Things to know

- **Sampling.** Current Claude models reject non-default `temperature`, so samples use each model's default sampling
  and there is no greedy run (see PREREGISTRATION.md, Deviations).
- **Sandbox.** Generated code runs with `python -I` in an empty temp directory with CPU, file and process limits, an
  address-space limit on Linux, and no network: `sandbox-exec` on macOS, `unshare -rn` on Linux. Where neither works,
  code still runs and every result records `network_isolation: "none"`, which the report flags. This guards against
  accidents, not a determined attacker; don't run it on a machine with secrets you can't afford to leak.
- **pandas** must be importable by the Python running the benchmark (`python -I` ignores user site-packages, so
  install it in the venv).
- **Adding a provider.** Subclass `Provider` in `providers.py`, register it in `PROVIDERS`, and add a model entry
  with `provider: <name>` to `models.yaml`.
- **Integrity.** Don't edit tasks after seeing results. List a flawed task in `INVALID.json`
  (`[{"task": "13_units_sold_by_product", "reason": "..."}]`) and the report shows the headline with and without it.
