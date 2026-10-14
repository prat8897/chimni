"""Run the benchmark.

    python -m benchmarks.llm.run --dry-run                 # mock model, free, writes results/dryrun/
    python -m benchmarks.llm.run --freeze                  # hash tasks + prompts into FROZEN.json (before real runs)
    python -m benchmarks.llm.run --max-cost 20             # real models from models.yaml, hard stop at $20

Every model reply is cached on disk under a hash of the full request (plus the sample index), so a rerun costs
nothing for replies already fetched. Results go to results/attempts.jsonl (real) or results/dryrun/attempts.jsonl.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import prompts, score
from .common import CONDITIONS, HERE, RESULTS_DIR, ROOT, load_tasks
from .providers import PROVIDERS

CACHE_DIR = HERE / "cache"
FROZEN = HERE / "FROZEN.json"


class BudgetExceeded(Exception):
    pass


# ------------------------------------------------------------------ config
def load_models(path):
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML is required: pip install -r benchmarks/llm/requirements.txt")
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return cfg["defaults"], cfg["models"]


def pick_models(models, names, dry_run):
    if dry_run:
        chosen = [m for m in models if m.get("dry_run")]
    elif names:
        chosen = [m for m in models if m["name"] in names and not m.get("dry_run")]
        missing = set(names) - {m["name"] for m in chosen}
        if missing:
            raise SystemExit(f"unknown model(s): {', '.join(sorted(missing))}")
    else:
        chosen = [m for m in models if m.get("enabled") and not m.get("dry_run")]
    if not chosen:
        raise SystemExit("no models selected")
    return chosen


# ------------------------------------------------------------------ freeze
def frozen_state():
    """Hashes of everything that defines the benchmark's questions: task files, prompt files, the docs shown to
    the chimni condition, and every rendered prompt."""
    files = {}
    for base in [HERE / "tasks", HERE / "prompts"]:
        for p in sorted(base.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                files[str(p.relative_to(HERE))] = hashlib.sha256(p.read_bytes()).hexdigest()
    for doc in ["docs/SPEC.md", "docs/TUTORIAL.md"]:
        files[doc] = hashlib.sha256((ROOT / doc).read_bytes()).hexdigest()
    rendered = hashlib.sha256()
    for c in CONDITIONS:
        rendered.update(prompts.system_prompt(c).encode())
        for t in load_tasks():
            if t.has(c):
                rendered.update(prompts.user_prompt(t, c).encode())
    return {"files": files, "rendered_prompts_sha256": rendered.hexdigest()}


def check_frozen():
    if not FROZEN.exists():
        raise SystemExit("FROZEN.json is missing. Review the tasks and prompts, then run --freeze before a real run.")
    want = json.loads(FROZEN.read_text(encoding="utf-8"))
    now = frozen_state()
    changed = sorted(k for k in set(want["files"]) | set(now["files"])
                     if want["files"].get(k) != now["files"].get(k))
    if changed or want["rendered_prompts_sha256"] != now["rendered_prompts_sha256"]:
        raise SystemExit("tasks or prompts changed since they were frozen:\n  " + "\n  ".join(changed or ["(rendered prompts)"])
                         + "\nDo not edit tasks after seeing results; mark flawed tasks in INVALID.json instead.")
    return want


# ---------------------------------------------------------- cost & cache
def cost_usd(usage, price):
    return (usage.get("input_tokens", 0) * price["input"]
            + usage.get("cache_creation_input_tokens", 0) * price["cache_write"]
            + usage.get("cache_read_input_tokens", 0) * price["cache_read"]
            + usage.get("output_tokens", 0) * price["output"]) / 1e6


class Ledger:
    """Hard spending limit. Before each uncached call, the worst case (whole prompt at the cache-write rate, plus
    max_tokens of output) is reserved; the reservation is replaced by the real cost when the reply arrives."""

    def __init__(self, limit):
        self.limit, self.spent, self.reserved = limit, 0.0, 0.0
        self.lock = threading.Lock()
        self.stopped = False

    def reserve(self, amount):
        with self.lock:
            if self.limit is not None and self.spent + self.reserved + amount > self.limit:
                self.stopped = True
                raise BudgetExceeded()
            self.reserved += amount

    def settle(self, reserved, actual):
        with self.lock:
            self.reserved -= reserved
            self.spent += actual


def request_key(model, system, messages, max_tokens, sample):
    blob = json.dumps({"provider": model["provider"], "model": model["id"], "temperature": model.get("temperature"),
                       "effort": model.get("effort"), "system": system, "messages": messages,
                       "max_tokens": max_tokens, "sample": sample}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def cache_path(cache_dir, key):
    return cache_dir / key[:2] / f"{key}.json"


# ---------------------------------------------------------------- tokens
def _tiktoken():
    try:
        import tiktoken
        return {name: tiktoken.get_encoding(name) for name in ("cl100k_base", "o200k_base")}
    except Exception:  # noqa: BLE001 - optional dependency, or encodings unavailable offline
        return {}


ENCODERS = _tiktoken()


def code_tokens(code, provider, cache_dir):
    out = {name: len(enc.encode(code)) for name, enc in ENCODERS.items()}
    if provider.count_tokens(None, [{"role": "user", "content": "x"}]) is None:
        return out
    key = hashlib.sha256(("count|" + provider.cfg["id"] + "|" + code).encode()).hexdigest()
    p = cache_path(cache_dir, key)
    if p.exists():
        out["anthropic"] = json.loads(p.read_text())["tokens"]
        return out
    base = provider.count_tokens(None, [{"role": "user", "content": "x"}])
    n = provider.count_tokens(None, [{"role": "user", "content": code}]) - base + 1
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"tokens": n}))
    out["anthropic"] = n
    return out


# ----------------------------------------------------------------- chains
def run_chain(job, ctx):
    """One sample: the first attempt plus up to `repair_attempts` repairs. Returns the attempt records."""
    model, provider, task, cond, sample = job
    system = prompts.system_prompt(cond)
    messages = [{"role": "user", "content": prompts.user_prompt(task, cond)}]
    records = []
    for attempt in range(1, ctx["repair_attempts"] + 2):
        if ctx["ledger"].stopped:
            break
        key = request_key(model, system, messages, ctx["max_tokens"], sample)
        cp = cache_path(ctx["cache_dir"], key)
        cached = cp.exists()
        if cached:
            reply = json.loads(cp.read_text(encoding="utf-8"))
        else:
            worst = cost_usd({"cache_creation_input_tokens": (len(system) + sum(len(m["content"]) for m in messages)) // 2,
                              "output_tokens": ctx["max_tokens"]}, model["price"])
            try:
                ctx["ledger"].reserve(worst)
            except BudgetExceeded:
                break
            t0 = time.time()
            try:
                r = provider.complete(system, messages, ctx["max_tokens"],
                                      {"task": task.id, "condition": cond, "sample": sample, "attempt": attempt})
            except Exception as e:  # noqa: BLE001 - API errors are recorded, not counted as model failures
                ctx["ledger"].settle(worst, 0.0)
                records.append(base_record(model, task, cond, sample, attempt, key, False) |
                               {"category": "api_error", "message": f"{type(e).__name__}: {e}"[:500]})
                break
            reply = {"text": r.text, "usage": r.usage, "stop_reason": r.stop_reason, "seconds": round(time.time() - t0, 2)}
            ctx["ledger"].settle(worst, cost_usd(r.usage, model["price"]))
            cp.parent.mkdir(parents=True, exist_ok=True)
            cp.write_text(json.dumps(reply), encoding="utf-8")
        code, result = score.score_reply(task.id, cond, reply["text"])
        rec = base_record(model, task, cond, sample, attempt, key, cached) | {
            "category": result["category"], "static_ok": result["static_ok"], "ran": result["ran"],
            "passed": result["passed"], "message": result.get("message", ""),
            "failing_kind": (result.get("failing") or {}).get("kind"),
            "network_isolation": result.get("network_isolation"),
            "usage": reply["usage"], "stop_reason": reply.get("stop_reason"),
            "cost_usd": 0.0 if cached else cost_usd(reply["usage"], model["price"]),
            "billed_cost_usd": cost_usd(reply["usage"], model["price"]),
            "response": reply["text"], "code": code,
            "code_chars": len(code) if code else None,
            "code_tokens": code_tokens(code, provider, ctx["cache_dir"]) if result["passed"] else None,
        }
        records.append(rec)
        stop = result["passed"] or (result["category"] == "declined" and not task.expressible)
        if stop or attempt > ctx["repair_attempts"]:
            break
        messages = messages + [{"role": "assistant", "content": reply["text"] or "(empty reply)"},
                               {"role": "user", "content": score.feedback(result, cond)}]
    return records


def base_record(model, task, cond, sample, attempt, key, cached):
    return {"model": model["name"], "model_id": model["id"], "task": task.id, "difficulty": task.difficulty,
            "expressible": task.expressible, "condition": cond, "sample": sample, "attempt": attempt,
            "request_hash": key, "cached": cached}


# ------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m benchmarks.llm.run", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="use the mock model; no API calls, no cost")
    ap.add_argument("--max-cost", type=float, help="hard stop in USD (required for real runs)")
    ap.add_argument("--freeze", action="store_true", help="write FROZEN.json from the current tasks and prompts")
    ap.add_argument("--models", help="comma-separated model names from models.yaml (default: enabled ones)")
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--tasks", help="comma-separated task ids or numbers (default: all)")
    ap.add_argument("--samples", type=int, help="samples per (task, condition, model); default from models.yaml")
    ap.add_argument("--no-repair", action="store_true", help="first attempts only")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--config", default=str(HERE / "models.yaml"))
    ap.add_argument("--out", help="results directory (default: results/ or results/dryrun/)")
    args = ap.parse_args(argv)

    if args.freeze:
        state = frozen_state() | {"frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                  "git_commit": git_commit()}
        FROZEN.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        print(f"froze {len(state['files'])} files; rendered prompts {state['rendered_prompts_sha256'][:12]}")
        return 0

    defaults, all_models = load_models(args.config)
    models = pick_models(all_models, args.models.split(",") if args.models else None, args.dry_run)
    if not args.dry_run:
        if args.max_cost is None:
            raise SystemExit("real runs need --max-cost (USD). Use --dry-run to test the pipeline for free.")
        frozen = check_frozen()
    else:
        frozen = None
    conditions = [c.strip() for c in args.conditions.split(",")]
    tasks = load_tasks(args.tasks.split(",") if args.tasks else None)
    out_dir = Path(args.out) if args.out else (RESULTS_DIR / "dryrun" if args.dry_run else RESULTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = CACHE_DIR / ("dryrun" if args.dry_run else "live")
    n = args.samples or defaults["samples"]
    ctx = {"ledger": Ledger(args.max_cost), "max_tokens": defaults["max_tokens"], "cache_dir": cache_dir,
           "repair_attempts": 0 if args.no_repair else defaults["repair_attempts"]}
    providers = {m["name"]: PROVIDERS[m["provider"]](m) for m in models}

    # sample-major order, so a run stopped by --max-cost still covers every task evenly
    jobs = [(m, providers[m["name"]], t, c, s) for s in range(n) for m in models for c in conditions
            for t in tasks if t.has(c)]
    print(f"{len(jobs)} chains: {len(models)} model(s) x {len(conditions)} condition(s) x {len(tasks)} task(s) "
          f"x {n} sample(s), up to {ctx['repair_attempts'] + 1} attempts each"
          + (f"; budget ${args.max_cost:.2f}" if args.max_cost is not None else ""))
    started = dt.datetime.now(dt.timezone.utc)
    records, done = [], 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for recs in pool.map(lambda j: run_chain(j, ctx), jobs):
            records.extend(recs)
            done += 1
            if done % 50 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)} chains, spent ${ctx['ledger'].spent:.2f}", flush=True)

    with open(out_dir / "attempts.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")
    meta = {
        "mode": "dry-run" if args.dry_run else "live",
        "started": started.isoformat(timespec="seconds"),
        "finished": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(), "frozen": frozen and {"git_commit": frozen.get("git_commit"),
                                                          "frozen_at": frozen.get("frozen_at"),
                                                          "rendered_prompts_sha256": frozen["rendered_prompts_sha256"]},
        "models": [{k: m.get(k) for k in ("name", "provider", "id", "temperature", "effort", "price")} for m in models],
        "conditions": conditions, "tasks": [t.id for t in tasks], "samples": n,
        "repair_attempts": ctx["repair_attempts"], "max_tokens": ctx["max_tokens"],
        "max_cost_usd": args.max_cost, "spent_usd": round(ctx["ledger"].spent, 4),
        "budget_stop": ctx["ledger"].stopped, "chains": len(jobs), "attempts": len(records),
        "python": sys.version.split()[0], "prompt_tokens": prompt_token_counts(conditions, models, providers),
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} attempts to {out_dir / 'attempts.jsonl'}; spent ${ctx['ledger'].spent:.2f}"
          + ("  ** stopped by --max-cost **" if ctx["ledger"].stopped else ""))
    print(f"report: python -m benchmarks.llm.report{' --dry-run' if args.dry_run else ''}")
    return 0


def prompt_token_counts(conditions, models, providers):
    out = {}
    for c in conditions:
        s = prompts.system_prompt(c)
        row = {"chars": len(s)} | {name: len(enc.encode(s)) for name, enc in ENCODERS.items()}
        for m in models:
            try:
                n = providers[m["name"]].count_tokens(s, [{"role": "user", "content": "x"}])
            except Exception:  # noqa: BLE001
                n = None
            if n is not None:
                row[f"anthropic:{m['name']}"] = n
        out[c] = row
    return out


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return None


if __name__ == "__main__":
    sys.exit(main())
