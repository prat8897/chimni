"""Extraction, comparison, failure categories and repair feedback."""
import unittest

from benchmarks.llm import score
from benchmarks.llm.common import same

TASK = "09_orders_per_customer"


class Extraction(unittest.TestCase):
    def test_prefers_the_block_tagged_with_the_right_language(self):
        text = "First:\n```text\nnot this\n```\nthen\n```python\ndef solve():\n    pass\n```"
        self.assertEqual(score.extract(text, "python")[0], "def solve():\n    pass\n")

    def test_falls_back_to_the_first_block(self):
        self.assertEqual(score.extract("```\nSELECT 1\n```", "sql")[0], "SELECT 1\n")

    def test_decline_is_only_recognised_for_chimni(self):
        self.assertEqual(score.extract("CANNOT_EXPRESS: no OR", "chimni"), (None, True))
        self.assertEqual(score.extract("CANNOT_EXPRESS: no OR", "python"), (None, False))

    def test_no_block(self):
        self.assertEqual(score.extract("just prose", "sql"), (None, False))


class Comparison(unittest.TestCase):
    def test_tuples_and_lists_are_equal(self):
        self.assertTrue(same([("a", 1)], [["a", 1]]))

    def test_floats_get_a_tiny_tolerance_but_no_more(self):
        self.assertTrue(same(0.1 + 0.2, 0.3))
        self.assertFalse(same(0.3, 0.31))
        self.assertTrue(same(3, 3.0))

    def test_none_bools_and_nan(self):
        self.assertFalse(same(None, 0))
        self.assertFalse(same(True, 1))
        self.assertFalse(same(float("nan"), float("nan")))
        self.assertFalse(same("1", 1))


class Categories(unittest.TestCase):
    def cat(self, cond, code):
        return score.score_code(TASK, cond, code)["category"]

    def test_python(self):
        self.assertEqual(self.cat("python", "def solve(orders):\n    return []\n"), "wrong_output")
        self.assertEqual(self.cat("python", "def solve(orders:\n"), "static")
        self.assertEqual(self.cat("python", "def solve(orders):\n    return orders[0]['nope']\n"), "runtime")
        self.assertEqual(self.cat("python", "import os\nos.nope()\n"), "runtime")
        self.assertEqual(self.cat("python", "def solve(orders):\n    while True:\n        pass\n"), "timeout")

    def test_chimni(self):
        self.assertEqual(self.cat("chimni", "$[orders]{(customer,count)}\n@orders  #(customer)  +n  ^\n"),
                         "wrong_output")                                   # forgot to sort
        self.assertEqual(self.cat("chimni", "$[orders]{(customer,count)}\n@orders  #(customer)  ^\n"), "runtime")
        self.assertEqual(self.cat("chimni", "$[orders]{(a,b)}\n@order  ^\n"), "static")

    def test_sql(self):
        self.assertEqual(self.cat("sql", "SELECT customer, COUNT(*) FROM orders GROUP BY customer"), "wrong_output")
        self.assertEqual(self.cat("sql", "SELEC 1"), "static")
        self.assertEqual(self.cat("sql", "SELECT nope FROM orders"), "static")
        self.assertEqual(self.cat("sql", "SELECT abs(-9223372036854775808)"), "runtime")


class Feedback(unittest.TestCase):
    def test_edge_case_inputs_are_shown(self):
        r = score.score_code(TASK, "python", "def solve(orders):\n    return [1]\n")
        self.assertEqual(r["failing"]["kind"], "edge")
        msg = score.feedback(r, "python")
        self.assertIn("Expected:", msg)
        self.assertIn("```python", msg)

    def test_random_inputs_are_never_shown(self):
        # passes the edge cases (empty list, and the hand-made tie) but not the random inputs
        code = ("def solve(orders):\n"
                "    if len(orders) != 4:\n"
                "        return [] if not orders else [('x', 0)]\n"
                "    return [('c', 2), ('b', 1), ('a', 1)]\n")
        r = score.score_code(TASK, "python", code)
        self.assertEqual(r["category"], "wrong_output")
        self.assertEqual(r["failing"]["kind"], "random")
        msg = score.feedback(r, "python")
        self.assertIn("hidden test input", msg)
        self.assertNotIn("customer", msg)

    def test_static_errors_are_fed_back_verbatim(self):
        r = score.score_code(TASK, "chimni", "$[orders]{n}\n@orders  ?>[limit]  ^\n")
        self.assertIn("unknown name `limit`", score.feedback(r, "chimni"))


if __name__ == "__main__":
    unittest.main()
