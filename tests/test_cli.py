"""The command line, run as a real subprocess: data from files, stdin, CSV; output formats; fmt."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDERS_CSV = "customer,amount\nasha,120\nravi,40\nasha,80\nmeera,300\nravi,25\n"


def chimni(*args, stdin=None):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, "-m", "chimni", *args], input=stdin, capture_output=True, text=True,
                          env=env, cwd=ROOT, stdin=None if stdin is not None else subprocess.DEVNULL)


class Run(unittest.TestCase):
    def test_inline_program_reads_csv_from_stdin(self):
        r = chimni("@orders  #(customer)  +s(amount)  ~\\(total)  ^", stdin=ORDERS_CSV)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [{"customer": "meera", "total": 300},
                                                {"customer": "asha", "total": 200},
                                                {"customer": "ravi", "total": 65}])

    def test_json_list_on_stdin_binds_to_the_only_input(self):
        r = chimni("@xs  ?>[2]  ~\\  ^", stdin="[1, 5, 3]")
        self.assertEqual(json.loads(r.stdout), [5, 3])

    def test_arg_sets_an_input(self):
        r = chimni("@xs  ?>[limit]  ^", "--arg", "limit=2", "-c", stdin="[1, 5, 3]")
        self.assertEqual(r.stdout.strip(), "[5,3]")

    def test_classic_file_and_json_file(self):
        r = chimni("examples/02_spenders_and_revenue.chimni", "@examples/inputs/02_spenders_and_revenue.json")
        self.assertEqual(json.loads(r.stdout), [[["meera", 300], ["asha", 200]], 565])

    def test_classic_json_literal_and_repr(self):
        r = chimni("examples/10_grade.chimni", '{"score": 91}', "-o", "repr")
        self.assertEqual(r.stdout.strip(), "'A'")

    def test_files_bind_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = json.loads((ROOT / "examples/inputs/08_top_customers_sql.json").read_text())
            (Path(tmp) / "customers.json").write_text(json.dumps(data["customers"]))
            (Path(tmp) / "o.json").write_text(json.dumps(data["orders"]))
            r = chimni("examples/08_top_customers_sql.chimni", f"orders={tmp}/o.json", f"{tmp}/customers.json")
        self.assertEqual(json.loads(r.stdout), [["meera", 300], ["asha", 201], ["kiran", 77]])

    def test_csv_output(self):
        r = chimni("@orders  #(customer)  +n  ^", "-o", "csv", stdin=ORDERS_CSV)
        self.assertEqual(r.stdout.splitlines(), ["customer,count", "asha,2", "ravi,2", "meera,1"])

    def test_trace_goes_to_stderr(self):
        r = chimni("@xs  ~/  ^", "--trace", stdin="[2, 1]")
        self.assertEqual(json.loads(r.stdout), [1, 2])
        self.assertIn("r1c2", r.stderr)

    def test_errors_exit_nonzero_with_a_location(self):
        r = chimni("@xs  *(b)  ^", stdin='[{"a": 1}]')
        self.assertEqual(r.returncode, 1)
        self.assertIn("row 1, col 2", r.stderr)

    def test_file_program_without_data_just_checks_it(self):
        r = chimni("examples/10_grade.chimni")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("ok"))

    def test_inline_program_without_data_is_an_error(self):
        r = chimni("@xs  ^")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no data", r.stderr)


class SignatureInference(unittest.TestCase):
    def test_inputs_come_from_sources_brackets_and_ties(self):
        from chimni.cli import infer_signature
        src = "@orders  ?(amount)>[limit]  ?>=[cut:A, _:B]  ^\n@orders  +s(amount)  ^\n.  '*rate  ^"
        self.assertTrue(infer_signature(src).startswith("$[orders,limit,cut,rate]{out1|none,out2|none,out3|none}"))

    def test_programs_with_a_signature_are_left_alone(self):
        from chimni.cli import infer_signature
        self.assertEqual(infer_signature("$[x]{y}\n@x  ^"), "$[x]{y}\n@x  ^")


class Fmt(unittest.TestCase):
    def test_examples_are_formatted(self):
        r = chimni("fmt", "--check", *sorted(str(p) for p in (ROOT / "examples").glob("*.chimni")))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_aligns_columns_and_keeps_comments(self):
        r = chimni("fmt", stdin="$[a,b]{x,y}\n-- note\n@a  +s ^\n@bb .   +s  ^  -- tail\n")
        self.assertEqual(r.stdout, "$[a,b]{x,y}\n-- note\n@a   +s  ^\n@bb  .   +s  ^  -- tail\n")

    def test_formatting_never_changes_meaning(self):
        import chimni as lib
        from chimni.fmt import format_source
        src = "$[s]{(c,v)}\n@s #(c) +s(x)\n@s . +s(x)\n. . ''/' ^\n"
        out = format_source(src)
        self.assertEqual(format_source(out), out)
        rows = lambda t: [[c.text for c in r] for r in lib.compile_source(t).rows]
        self.assertEqual(rows(src), rows(out))

    def test_check_flags_unformatted_files(self):
        with tempfile.NamedTemporaryFile("w", suffix=".chimni", delete=False) as f:
            f.write("$[a]{b}\n@a ?>[1] +n ^\n")
        try:
            self.assertEqual(chimni("fmt", "--check", f.name).returncode, 1)
            self.assertEqual(chimni("fmt", "-w", f.name).returncode, 0)
            self.assertEqual(chimni("fmt", "--check", f.name).returncode, 0)
        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
