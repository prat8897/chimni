"""Differential tests: every example, run as Chimni and as the original Python, on random inputs.

The idiomatic pandas / SQL / jq versions in examples/compare/ are held to the same standard.
If two versions ever disagree, the test fails and prints the input that broke it.
"""
import functools
import importlib.util
import inspect
import json
import random
import re
import shutil
import sqlite3
import subprocess
import unittest
from pathlib import Path

import chimni

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
NAMES = ["asha", "ravi", "meera", "kiran", "dev", "zoya"]
RUNS = 300


@functools.lru_cache(maxsize=None)
def reference(stem, folder="python"):
    spec = importlib.util.spec_from_file_location("ref_" + stem, EX / folder / (stem + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (fn,) = [v for v in vars(mod).values() if inspect.isfunction(v)]
    return fn


# ---- random input generators, one per input shape ----
def g_orders(r):
    o = [{"customer": r.choice(NAMES), "amount": r.randint(1, 300)} for _ in range(r.randint(0, 12))]
    return dict(orders=o, min_total=r.randint(0, 400))


def g_transactions(r):
    t = [{"id": r.randint(1, 6), "amount": r.randint(1, 100)} for _ in range(r.randint(0, 10))]
    return dict(transactions=t, limit=r.randint(0, 100))


def g_users(r):
    return dict(users=[{"name": r.choice(NAMES) + str(r.randint(0, 9)), "age": r.randint(5, 90)}
                       for _ in range(r.randint(0, 10))])


def g_text(r):
    words = ["the", "The", "cat", "sat", "on", "mat", "A", "a", "dog"]
    return dict(text=" ".join(r.choice(words) for _ in range(r.randint(0, 15))), n=r.randint(0, 5))


def g_sales(r):
    return dict(sales=[{"cat": r.choice(["food", "toys", "books"]), "amount": r.randint(1, 200)}
                       for _ in range(r.randint(0, 10))])


def g_join(r):
    cs = [{"id": i, "name": r.choice(NAMES)} for i in range(1, r.randint(1, 8))]
    os_ = [{"id": k, "cid": r.randint(1, 9), "amount": r.randint(1, 200)} for k in range(r.randint(0, 14))]
    return dict(customers=cs, orders=os_)


def g_expenses(r):
    return dict(expenses=[r.randint(0, 50) for _ in range(r.randint(0, 10))], budget=r.randint(0, 200))


def g_score(r):
    return dict(score=r.randint(0, 100))


CASES = [
    ("01_big_spenders", g_orders),
    ("02_spenders_and_revenue", g_orders),
    ("03_first_big_new_transaction", g_transactions),
    ("04_adult_names", g_users),
    ("05_top_words", g_text),
    ("06_category_share", g_sales),
    ("07_oldest_user", g_users),
    ("08_top_customers_sql", g_join),
    ("09_first_overspend", g_expenses),
    ("10_grade", g_score),
]


class DifferentialTests(unittest.TestCase):
    def test_every_example_matches_its_python_original(self):
        for stem, gen in CASES:
            with self.subTest(example=stem):
                prog = chimni.load(str(EX / (stem + ".chimni")))
                ref = reference(stem)
                rng = random.Random(stem)
                for _ in range(RUNS):
                    args = gen(rng)
                    self.assertEqual(prog.run(args), ref(**args), msg=f"input: {args}")

    def test_every_example_has_a_python_original_and_a_test(self):
        on_disk = sorted(p.stem for p in EX.glob("*.chimni"))
        self.assertEqual(on_disk, sorted(s for s, _ in CASES))
        self.assertEqual(on_disk, sorted(p.stem for p in (EX / "python").glob("*.py")))


# ---- the fair comparison: pandas / SQL / jq ----
def alternative(stem):
    """Return (language, callable) for examples/compare/<stem>.*"""
    (path,) = list((EX / "compare").glob(stem + ".*"))
    if path.suffix == ".py":
        return "pandas", lambda **args: reference(stem, "compare")(**args)
    if path.suffix == ".jq":
        return "jq", lambda **args: run_jq(path, args)
    return "sql", lambda **args: run_sql(path, stem, args)


def run_jq(path, args):
    out = subprocess.run(["jq", "-c", "-f", str(path)], input=json.dumps(args),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def run_sql(path, stem, args):
    """Load each list input into a table (columns from the `-- tables:` line), run each statement."""
    src = path.read_text(encoding="utf-8")
    db = sqlite3.connect(":memory:")
    for table, cols in re.findall(r"(\w+)\(([^)]*)\)", re.search(r"-- tables: (.*)", src).group(1)):
        cols = [c.strip() for c in cols.split(",")]
        db.execute(f"create table {table}({', '.join(cols)})")
        db.executemany(f"insert into {table} values ({', '.join('?' * len(cols))})",
                       [tuple(row[c] for c in cols) for row in args[table]])
    params = {k: v for k, v in args.items() if not isinstance(v, list)}
    body = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("--"))
    slots = chimni.load(str(EX / (stem + ".chimni"))).slots
    results = []
    for slot, stmt in zip(slots, [q for q in body.split(";") if q.strip()]):
        rows = db.execute(stmt, params).fetchall()
        results.append([tuple(r) for r in rows] if slot.fields else (rows[0][0] if rows else None))
    return results[0] if len(results) == 1 else tuple(results)


def available(lang):
    if lang == "pandas":
        return importlib.util.find_spec("pandas") is not None
    if lang == "jq":
        return shutil.which("jq") is not None
    return True


class FairComparison(unittest.TestCase):
    def test_every_example_has_exactly_one_alternative(self):
        on_disk = sorted(p.stem for p in (EX / "compare").iterdir() if p.is_file())
        self.assertEqual(on_disk, sorted(s for s, _ in CASES))

    def test_alternatives_match_chimni(self):
        for stem, gen in CASES:
            lang, alt = alternative(stem)
            with self.subTest(example=stem, lang=lang):
                if not available(lang):
                    self.skipTest(f"{lang} is not installed")
                prog = chimni.load(str(EX / (stem + ".chimni")))
                rng = random.Random("alt" + stem)
                runs = RUNS if lang != "jq" else 60      # jq is a subprocess per run
                for _ in range(runs):
                    args = gen(rng)
                    self.assertEqual(alt(**args), prog.run(args), msg=f"input: {args}")


class SampleInputs(unittest.TestCase):
    def test_every_example_runs_on_its_sample_input(self):
        for stem, _ in CASES:
            with self.subTest(example=stem):
                args = json.loads((EX / "inputs" / (stem + ".json")).read_text(encoding="utf-8"))
                self.assertEqual(chimni.load(str(EX / (stem + ".chimni"))).run(args), reference(stem)(**args))


class KeyedTies(unittest.TestCase):
    """Two grouped rows combined by a tie pair up by key, not by position."""

    def test_groups_in_a_different_order_still_pair_by_key(self):
        prog = chimni.compile_source(
            "$[sales,returns]{(category,ratio)}\n"
            "@sales    #(category)  +s(revenue)\n"
            "@returns  #(category)  +s(units)\n"
            ".         .            ''/'          ^\n")
        got = prog(sales=[{"category": "a", "revenue": 10}, {"category": "b", "revenue": 100}],
                   returns=[{"category": "b", "units": 1}, {"category": "a", "units": 10}])
        self.assertEqual(got, [("a", 1.0), ("b", 100.0)])

    def test_plain_streams_still_pair_by_position(self):
        prog = chimni.compile_source("$[xs,ys]{zs}\n@xs\n@ys\n''-'  ^\n")
        self.assertEqual(prog(xs=[10, 20], ys=[1, 2]), [9, 18])


class FixedExamples(unittest.TestCase):
    def test_summarize_orders_from_the_original_conversation(self):
        orders = [{"customer": "asha", "amount": 120}, {"customer": "ravi", "amount": 40},
                  {"customer": "asha", "amount": 80}, {"customer": "meera", "amount": 300},
                  {"customer": "ravi", "amount": 25}]
        prog = chimni.load(str(EX / "01_big_spenders.chimni"))
        self.assertEqual(prog(orders, min_total=100), [("meera", 300), ("asha", 200)])

    def test_join_example_matches_the_real_sql_run_by_sqlite(self):
        customers = [{"id": 1, "name": "asha"}, {"id": 2, "name": "ravi"}, {"id": 3, "name": "meera"},
                     {"id": 4, "name": "kiran"}, {"id": 5, "name": "dev"}]
        orders = [{"id": 1, "cid": 1, "amount": 120}, {"id": 2, "cid": 2, "amount": 40},
                  {"id": 3, "cid": 1, "amount": 81}, {"id": 4, "cid": 3, "amount": 300},
                  {"id": 5, "cid": 2, "amount": 25}, {"id": 6, "cid": 4, "amount": 77},
                  {"id": 7, "cid": 5, "amount": 5}, {"id": 8, "cid": 9, "amount": 999}]
        db = sqlite3.connect(":memory:")
        db.execute("create table customers(id int, name text)")
        db.execute("create table orders(id int, cid int, amount int)")
        db.executemany("insert into customers values (?,?)", [(c["id"], c["name"]) for c in customers])
        db.executemany("insert into orders values (?,?,?)", [(o["id"], o["cid"], o["amount"]) for o in orders])
        want = [tuple(r) for r in db.execute(
            "SELECT c.name, SUM(o.amount) FROM customers c JOIN orders o ON o.cid = c.id "
            "GROUP BY c.name ORDER BY 2 DESC LIMIT 3")]
        got = chimni.load(str(EX / "08_top_customers_sql.chimni"))(customers, orders)
        self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
