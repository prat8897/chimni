"""End to end with the mock model: run, cache, cost limit, freeze check, report."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmarks.llm import report, run

TASKS = "01,09,24,27"
needs_yaml = unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML is not installed")


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a)


@needs_yaml
class DryRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.cache = mock.patch.object(run, "CACHE_DIR", cls.out / "cache")
        cls.cache.start()
        quiet(run.main, ["--dry-run", "--tasks", TASKS, "--samples", "3", "--out", str(cls.out / "a")])
        quiet(run.main, ["--dry-run", "--tasks", TASKS, "--samples", "3", "--out", str(cls.out / "b")])

    @classmethod
    def tearDownClass(cls):
        cls.cache.stop()
        cls.tmp.cleanup()

    def rows(self, name):
        return [json.loads(x) for x in (self.out / name / "attempts.jsonl").read_text().splitlines()]

    def test_every_chain_ran(self):
        rows = self.rows("a")
        firsts = [r for r in rows if r["attempt"] == 1]
        self.assertEqual(len(firsts), 4 * 4 * 3)          # tasks x conditions x samples
        self.assertTrue(all(r["category"] != "api_error" for r in rows))

    def test_failures_are_repaired_and_passes_are_not(self):
        rows = self.rows("a")
        chains = {}
        for r in rows:
            chains.setdefault((r["task"], r["condition"], r["sample"]), []).append(r)
        for v in chains.values():
            v.sort(key=lambda r: r["attempt"])
            for earlier in v[:-1]:
                self.assertFalse(earlier["passed"])
            self.assertLessEqual(len(v), 3)
        self.assertTrue(any(len(v) > 1 for v in chains.values()))

    def test_declining_an_inexpressible_task_ends_the_chain(self):
        rows = self.rows("a")
        last = {}
        for r in rows:
            k = (r["task"], r["condition"], r["sample"])
            last[k] = max(last.get(k, 0), r["attempt"])
        declined = [r for r in rows if r["task"].startswith("27") and r["condition"] == "chimni"
                    and r["category"] == "declined"]
        self.assertTrue(declined)
        for r in declined:
            self.assertEqual(r["attempt"], last[(r["task"], r["condition"], r["sample"])])

    def test_second_run_is_served_from_the_cache_and_identical(self):
        a, b = self.rows("a"), self.rows("b")
        self.assertTrue(all(r["cached"] for r in b))
        self.assertEqual(json.loads((self.out / "b" / "run_meta.json").read_text())["spent_usd"], 0)
        strip = lambda rows: sorted(json.dumps({k: v for k, v in r.items() if k not in ("cached", "cost_usd")},
                                               sort_keys=True) for r in rows)
        self.assertEqual(strip(a), strip(b))

    def test_correct_solutions_have_token_counts(self):
        ok = [r for r in self.rows("a") if r["passed"]]
        self.assertTrue(ok)
        for r in ok:
            self.assertGreater(r["code_chars"], 0)

    def test_report(self):
        with mock.patch.object(report, "RESULTS_DIR", self.out):
            quiet(report.main, ["--dir", str(self.out / "a")])
        text = (self.out / "a" / "REPORT.md").read_text()
        for heading in ["DRY RUN", "## Headline", "pass@1", "## How first attempts fail", "## Tokens",
                        "## Pre-registered hypotheses", "## Tasks Chimni cannot express", "## Where Chimni failed most"]:
            self.assertIn(heading, text)


@needs_yaml
class CostLimit(unittest.TestCase):
    def test_hard_stop(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(run, "CACHE_DIR", Path(tmp) / "cache"):
            # the mock is priced like Sonnet: each call reserves ~$0.17 (16k output tokens) and costs <$0.01
            quiet(run.main, ["--dry-run", "--tasks", TASKS, "--samples", "2", "--max-cost", "0.3",
                             "--workers", "1", "--out", tmp])
            meta = json.loads((Path(tmp) / "run_meta.json").read_text())
            self.assertTrue(meta["budget_stop"])
            self.assertLessEqual(meta["spent_usd"], 0.3)
            rows = (Path(tmp) / "attempts.jsonl").read_text().splitlines()
            self.assertGreater(len(rows), 0)
            self.assertLess(len(rows), 32)

    def test_ledger_reserves_the_worst_case(self):
        led = run.Ledger(1.0)
        led.reserve(0.6)
        with self.assertRaises(run.BudgetExceeded):
            led.reserve(0.6)
        led.settle(0.6, 0.1)
        led.reserve(0.6)


class RealRunGuards(unittest.TestCase):
    @needs_yaml
    def test_real_runs_need_a_cost_limit(self):
        with self.assertRaises(SystemExit) as cm:
            quiet(run.main, ["--tasks", "01"])
        self.assertIn("--max-cost", str(cm.exception))

    def test_frozen_check_catches_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            frozen = Path(tmp) / "FROZEN.json"
            state = run.frozen_state()
            key = next(iter(state["files"]))
            state["files"][key] = "0" * 64
            frozen.write_text(json.dumps(state))
            with mock.patch.object(run, "FROZEN", frozen), self.assertRaises(SystemExit) as cm:
                run.check_frozen()
            self.assertIn(key, str(cm.exception))

    def test_frozen_check_passes_when_nothing_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            frozen = Path(tmp) / "FROZEN.json"
            frozen.write_text(json.dumps(run.frozen_state()))
            with mock.patch.object(run, "FROZEN", frozen):
                run.check_frozen()


class Stats(unittest.TestCase):
    def test_pass_at_k(self):
        self.assertEqual(report.pass_at_k(5, 0, 1), 0)
        self.assertEqual(report.pass_at_k(5, 5, 3), 1)
        self.assertAlmostEqual(report.pass_at_k(5, 2, 1), 0.4)
        self.assertAlmostEqual(report.pass_at_k(5, 1, 3), 0.6)
        self.assertIsNone(report.pass_at_k(2, 1, 3))

    def test_bootstrap_brackets_the_mean(self):
        v, lo, hi = report.bootstrap([0, 0.5, 1, 1, 0.25], b=2000)
        self.assertLessEqual(lo, v)
        self.assertLessEqual(v, hi)


if __name__ == "__main__":
    unittest.main()
