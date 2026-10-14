"""The few-shot solutions are correct, and the prompts say what the harness does."""
import importlib.util
import json
import random
import unittest

import chimni

from benchmarks.llm import prompts, sandbox
from benchmarks.llm.common import PROMPTS_DIR, ROOT, load_tasks, same

HAS_PANDAS = importlib.util.find_spec("pandas") is not None


def generators():
    spec = importlib.util.spec_from_file_location("tex", ROOT / "tests" / "test_examples.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.CASES)


class FewShotsAreCorrect(unittest.TestCase):
    """Each few-shot solution must match the repository's Chimni example on random inputs."""

    def test_every_language(self):
        gens = generators()
        for d in sorted((PROMPTS_DIR / "fewshot").iterdir()):
            meta = json.loads((d / "meta.json").read_text())
            self.assertEqual((d / "solution.chimni").read_text(), (ROOT / "examples" / (d.name + ".chimni")).read_text())
            prog = chimni.load(str(d / "solution.chimni"))
            rng = random.Random(d.name)
            inputs = [gens[d.name](rng) for _ in range(150)]
            want = [prog.run(a) for a in inputs]
            for lang, f in [("python", "solution.py"), ("pandas", "solution_pandas.py"), ("sql", "solution.sql")]:
                if not (d / f).exists() or (lang == "pandas" and not HAS_PANDAS):
                    continue
                with self.subTest(example=d.name, lang=lang):
                    sq = meta.get("sql", {})
                    r = sandbox.run_solution(lang, (d / f).read_text(), inputs, tables=sq.get("tables"),
                                             sql_output=sq.get("output"))
                    self.assertEqual(r["status"], "ok", r)
                    self.assertIsNone(r["error"], r)
                    bad = [i for i, (g, w) in enumerate(zip(r["outputs"], want)) if not same(g, w)]
                    self.assertFalse(bad, bad and inputs[bad[0]])


class PromptContents(unittest.TestCase):
    def test_counts_of_few_shots(self):
        self.assertEqual(len(prompts.fewshots("chimni")), 10)
        self.assertEqual(len(prompts.fewshots("python")), 10)
        self.assertEqual(len(prompts.fewshots("pandas")), 10)
        self.assertEqual(len(prompts.fewshots("sql")), 8)      # no single-statement form for 02 and 05

    def test_only_chimni_gets_the_language_docs_and_the_decline_option(self):
        for c in ("python", "pandas", "sql"):
            self.assertNotIn("Chimni language reference", prompts.system_prompt(c))
            self.assertNotIn("CANNOT_EXPRESS", prompts.system_prompt(c))
        self.assertIn("Chimni language reference", prompts.system_prompt("chimni"))
        self.assertIn("CANNOT_EXPRESS", prompts.system_prompt("chimni"))

    def test_same_spec_text_in_every_condition(self):
        for t in load_tasks():
            for c in ("chimni", "python", "pandas", "sql"):
                if t.has(c):
                    self.assertIn(t.spec.strip(), prompts.user_prompt(t, c))

    def test_no_reference_solution_leaks_into_a_prompt(self):
        for t in load_tasks():
            for c in ("chimni", "python", "pandas", "sql"):
                ref = t.reference_code(c)
                if ref and t.has(c):
                    squeeze = lambda s: " ".join(s.split())
                    body = squeeze(ref.split('"""', 2)[-1] if c == "python" else ref)
                    self.assertNotIn(body, squeeze(prompts.system_prompt(c) + prompts.user_prompt(t, c)), (t.id, c))


if __name__ == "__main__":
    unittest.main()
