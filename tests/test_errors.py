"""Mistakes the language must catch, with messages a human can act on."""
import unittest

import chimni
from chimni import GrammarError, RunError


class GrammarChecks(unittest.TestCase):
    """Rejected before anything runs."""

    def bad(self, src, fragment):
        with self.assertRaises(GrammarError) as cm:
            chimni.compile_source(src)
        self.assertIn(fragment, str(cm.exception))

    def test_stage_with_nothing_on_its_left(self):
        self.bad("$[xs]{ys}\n.  ?>[1]  ^\n", "no input")

    def test_tie_reaching_above_the_first_row(self):
        self.bad("$[xs]{ys}\n@xs  '  ^\n", "row(s) up")

    def test_tie_onto_an_empty_cell(self):
        self.bad("$[xs]{a}\n.  .\n@xs  '  ^\n", "which is empty")

    def test_output_count_must_match_emits(self):
        self.bad("$[xs]{a,b}\n@xs  ^\n", "declares 2 output")

    def test_unknown_symbol(self):
        self.bad("$[xs]{a}\n@xs  !(x)  ^\n", "unknown symbol")

    def test_unknown_input(self):
        self.bad("$[xs]{a}\n@zs  ^\n", "no input named")

    def test_unknown_name_in_brackets(self):
        self.bad("$[xs]{a}\n@xs  ?>[limit]  ^\n", "unknown name")

    def test_nothing_may_follow_emit(self):
        self.bad("$[xs]{a}\n@xs  ^  ~/\n", "nothing may follow")

    def test_signature_is_required_first(self):
        self.bad("@xs  ^\n", "signature")


class RuntimeChecks(unittest.TestCase):
    """Caught while running, with the row and column."""

    def bad(self, src, args, fragment):
        prog = chimni.compile_source(src)
        with self.assertRaises(RunError) as cm:
            prog.run(args)
        self.assertIn(fragment, str(cm.exception))
        return cm.exception

    def test_output_shape_must_match_the_pipeline(self):
        # the "set vs. sorted pairs" class of bug: signature and rows disagree
        self.bad("$[orders]{(customer,total,extra)}\n@orders  #(customer)  +s(amount)  ^\n",
                 dict(orders=[{"customer": "a", "amount": 1}]), "expects 3 fields")

    def test_none_needs_permission_in_the_signature(self):
        self.bad("$[xs]{a}\n@xs  +m(v)  *(v)  ^\n", dict(xs=[]), "does not allow it")

    def test_none_is_fine_when_the_signature_says_so(self):
        prog = chimni.compile_source("$[xs]{a|none}\n@xs  +m(v)  *(v)  ^\n")
        self.assertIsNone(prog.run(dict(xs=[])))

    def test_forgot_to_aggregate_after_group(self):
        self.bad("$[xs]{a}\n@xs  #(k)  ^\n", dict(xs=[{"k": 1}]), "un-aggregated")

    def test_missing_field_lists_the_real_ones(self):
        self.bad("$[xs]{a}\n@xs  *(nope)  ^\n", dict(xs=[{"k": 1}]), "item has: k")

    def test_missing_and_unknown_inputs(self):
        self.bad("$[xs,n]{a}\n@xs  ^[n]\n", dict(xs=[]), "missing input")
        self.bad("$[xs]{a}\n@xs  ^\n", dict(xs=[], zz=1), "unknown input")

    def test_division_by_zero(self):
        e = self.bad("$[xs]{a}\n@xs  +s(v)\n@xs  +s(v)\n.  ''/'  ^\n", dict(xs=[{"v": 0}]), "division by zero")
        self.assertEqual((e.row, e.col), (3, 2))

    def test_errors_carry_row_and_column(self):
        e = self.bad("$[xs]{a}\n@xs  ?(v)>[1]  ^\n", dict(xs=[{"w": 1}]), "no field 'v'")
        self.assertEqual((e.row, e.col), (1, 2))


class LayoutSemantics(unittest.TestCase):
    def test_dot_passes_data_through(self):
        prog = chimni.compile_source("$[xs]{a}\n@xs  .  .  ~/  ^\n")
        self.assertEqual(prog.run(dict(xs=[3, 1, 2])), [1, 2, 3])

    def test_blank_lines_and_comments_are_ignored(self):
        prog = chimni.compile_source("-- hi\n$[xs]{a}\n\n@xs  ~\\  ^  -- trailing comment\n")
        self.assertEqual(prog.run(dict(xs=[1, 3, 2])), [3, 2, 1])

    def test_ties_do_arithmetic_with_numbers_and_precedence(self):
        prog = chimni.compile_source("$[xs]{a}\n@xs  +s\n.  '*2+1  ^\n")
        self.assertEqual(prog.run(dict(xs=[1, 2, 3])), 13)

    def test_independent_rows_do_not_see_each_other(self):
        prog = chimni.compile_source("$[xs]{a,b}\n@xs  ~/  ^\n@xs  ~\\  ^\n")
        self.assertEqual(prog.run(dict(xs=[2, 1, 3])), ([1, 2, 3], [3, 2, 1]))


if __name__ == "__main__":
    unittest.main()
