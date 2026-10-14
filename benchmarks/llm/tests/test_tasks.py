"""The task set is well-formed, and every reference solution agrees with every other one.

The python reference is the trusted one. The chimni, pandas and sql references are run through the same sandbox
and scorer the models' code goes through, on the same 300 random inputs plus the hand-written edge cases.
"""
import importlib.util
import json
import random
import unittest
from collections import Counter

from benchmarks.llm.common import N_RANDOM, load_tasks
from benchmarks.llm.score import score_code

HAS_PANDAS = importlib.util.find_spec("pandas") is not None
TASKS = load_tasks()


class TaskSetShape(unittest.TestCase):
    def test_thirty_tasks_with_every_file(self):
        self.assertEqual(len(TASKS), 30)
        for t in TASKS:
            with self.subTest(task=t.id):
                for f in ["spec.md", "reference.py", "input_gen.py", "edge_cases.json", "meta.json"]:
                    self.assertTrue((t.dir / f).exists(), f)
                self.assertEqual((t.dir / "reference.chimni").exists(), t.expressible)
                self.assertIn(t.difficulty, {"easy", "medium", "hard"})
                self.assertTrue(t.meta["features"])
                if not t.expressible:
                    self.assertTrue(t.meta.get("why_not_expressible"))
                for cond, f in [("pandas", "reference_pandas.py"), ("sql", "reference.sql")]:
                    self.assertEqual(t.has(cond), (t.dir / f).exists(), cond)
                self.assertGreaterEqual(len(t.edge_cases), 2)

    def test_mix_of_difficulties_and_four_inexpressible(self):
        self.assertEqual(Counter(t.difficulty for t in TASKS), {"easy": 9, "medium": 13, "hard": 8})
        self.assertEqual(sum(not t.expressible for t in TASKS), 4)

    def test_no_task_reuses_a_documented_example(self):
        from benchmarks.llm.common import ROOT
        examples = {p.read_text().strip() for p in (ROOT / "examples").glob("*.chimni")}
        for t in TASKS:
            code = t.reference_code("chimni")
            if code:
                self.assertNotIn(code.strip(), examples, t.id)

    def test_inputs_are_deterministic_and_match_the_declared_inputs(self):
        for t in TASKS:
            with self.subTest(task=t.id):
                a, b = t.test_inputs(), t.test_inputs()
                self.assertEqual(json.dumps(a), json.dumps(b))
                self.assertEqual(len(a), len(t.edge_cases) + N_RANDOM)
                for _, _, args in a:
                    self.assertEqual(sorted(args), sorted(t.inputs))

    def test_random_inputs_cover_the_empty_case(self):
        for t in TASKS:
            lists = [k for k, v in t.test_inputs()[-1][2].items() if isinstance(v, list)]
            if lists:
                empties = sum(1 for _, _, a in t.test_inputs() if not a[lists[0]])
                self.assertGreater(empties, 0, t.id)


class ReferencesAgree(unittest.TestCase):
    def check(self, cond):
        for t in TASKS:
            code = t.reference_code(cond)
            if code is None:
                continue
            with self.subTest(task=t.id, condition=cond):
                r = score_code(t.id, cond, code)
                self.assertEqual(r["category"], "pass", f"{r.get('message')} {r.get('failing')}")

    def test_python_reference_passes_its_own_harness(self):
        self.check("python")

    def test_chimni_references(self):
        self.check("chimni")

    def test_sql_references(self):
        self.check("sql")

    @unittest.skipUnless(HAS_PANDAS, "pandas is not installed")
    def test_pandas_references(self):
        self.check("pandas")


class GeneratorsAreSeeded(unittest.TestCase):
    def test_same_seed_same_inputs(self):
        from benchmarks.llm.common import _load_module
        t = TASKS[0]
        gen = _load_module(t.dir / "input_gen.py", "g").generate
        self.assertEqual(gen(random.Random(1)), gen(random.Random(1)))


if __name__ == "__main__":
    unittest.main()
