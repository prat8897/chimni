"""The docs make promises. These tests keep them."""
import re
import unittest
from pathlib import Path

import chimni

ROOT = Path(__file__).resolve().parent.parent
ORDERS = [{"customer": "asha", "amount": 120}, {"customer": "ravi", "amount": 40},
          {"customer": "asha", "amount": 80}, {"customer": "meera", "amount": 300},
          {"customer": "ravi", "amount": 25}]


class ReadmePromises(unittest.TestCase):
    def test_quickstart_output(self):
        prog = chimni.load(str(ROOT / "examples" / "02_spenders_and_revenue.chimni"))
        self.assertEqual(prog.run(dict(orders=ORDERS, min_total=100)), ([("meera", 300), ("asha", 200)], 565))

    def test_trace_shows_one_line_per_cell(self):
        prog = chimni.load(str(ROOT / "examples" / "01_big_spenders.chimni"))
        log = []
        prog.run(dict(orders=ORDERS, min_total=100), trace=log)
        self.assertEqual([line.split()[0] for line in log], ["r1c1", "r1c2", "r1c3", "r1c4", "r1c5", "r1c6"])

    def test_readme_error_example(self):
        prog = chimni.compile_source("$[orders]{(customer,total,extra)}\n@orders  #(customer)  +s(amount)  ^\n")
        with self.assertRaises(chimni.RunError) as cm:
            prog.run(dict(orders=[{"customer": "a", "amount": 1}]))
        self.assertEqual(str(cm.exception),
                         "run error at row 1, col 4: output (customer,total,extra) expects 3 fields "
                         "but items have 2: customer, total.")


class TutorialAnswers(unittest.TestCase):
    def test_bigger_than_limit_sorted(self):
        prog = chimni.compile_source("$[numbers,limit]{big}\n@numbers  ?>[limit]  ~\\  ^\n")
        self.assertEqual(prog.run(dict(numbers=[5, 20, 1, 12], limit=4)), [20, 12, 5])

    def test_count_minors(self):
        prog = chimni.compile_source("$[users]{minors}\n@users  ?(age)<[18]  +n  ^\n")
        self.assertEqual(prog.run(dict(users=[{"age": 10}, {"age": 30}, {"age": 17}])), 2)

    def test_adult_names_walkthrough(self):
        prog = chimni.compile_source("$[users]{names}\n@users  ?(age)>=[18]  *(name)  ~/  ^\n")
        users = [{"name": "zed", "age": 40}, {"name": "kid", "age": 9}, {"name": "amy", "age": 18}]
        self.assertEqual(prog.run(dict(users=users)), ["amy", "zed"])


class EveryChimniBlockInTheDocsParses(unittest.TestCase):
    def test_text_blocks_that_start_with_a_signature_compile(self):
        checked = 0
        for doc in [ROOT / "README.md", ROOT / "docs" / "TUTORIAL.md", ROOT / "docs" / "SPEC.md"]:
            for block in re.findall(r"```text\n(.*?)```", doc.read_text(encoding="utf-8"), re.S):
                if block.lstrip().startswith("$"):
                    with self.subTest(doc=doc.name, block=block.splitlines()[0]):
                        chimni.compile_source(block)
                    checked += 1
        self.assertGreaterEqual(checked, 6)


if __name__ == "__main__":
    unittest.main()
