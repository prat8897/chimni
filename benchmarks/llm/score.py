"""Extract code from a model reply, run it against the reference, and classify the outcome.

Categories (one per attempt):
  pass          every test input matched the reference
  declined      (chimni) the model answered CANNOT_EXPRESS instead of writing code
  extraction    the reply had no usable code block
  static        rejected before running on any input: Python SyntaxError, a Chimni grammar error,
                or an SQL statement SQLite refuses to compile
  runtime       raised an error while running on some input (incl. crashes)
  wrong_output  ran on every input but some output differed from the reference
  timeout       exceeded the time limit
"""
import re
from functools import lru_cache

from . import sandbox
from .common import load_tasks, same, short

FENCE = re.compile(r"```[ \t]*([\w+-]*)[^\n]*\n(.*?)```", re.S)
LANG_TAGS = {"chimni": {"chimni", "text", "txt", ""}, "python": {"python", "py", "python3"},
             "pandas": {"python", "py", "python3"}, "sql": {"sql", "sqlite", "sqlite3"}}
DECLINE = "CANNOT_EXPRESS"
CATEGORIES = ["pass", "wrong_output", "runtime", "static", "timeout", "extraction", "declined"]


def extract(text, condition):
    """Return (code or None, declined: bool)."""
    blocks = FENCE.findall(text or "")
    if not blocks:
        return None, DECLINE in (text or "") and condition == "chimni"
    for tag, body in blocks:
        if tag.lower() in LANG_TAGS[condition]:
            return body.strip("\n") + "\n", False
    return blocks[0][1].strip("\n") + "\n", False


@lru_cache(maxsize=None)
def _tests(task_id):
    (task,) = load_tasks([task_id])
    ref = task.reference_fn()
    tests = task.test_inputs()
    return task, tests, [ref(**args) for _, _, args in tests]


def score_code(task_id, condition, code):
    task, tests, expected = _tests(task_id)
    sql = task.meta.get("sql", {})
    res = sandbox.run_solution(condition, code, [t[2] for t in tests],
                               tables=sql.get("tables"), sql_output=sql.get("output"))
    out = {"network_isolation": res.get("network_isolation"), "n_tests": len(tests)}
    status = res["status"]
    if status == "timeout":
        return {**out, "category": "timeout", "static_ok": True, "ran": False, "passed": False,
                "message": f"timed out (over {sandbox.WALL_TIMEOUT}s for {len(tests)} inputs)"}
    if status == "crash":
        return {**out, "category": "runtime", "static_ok": True, "ran": False, "passed": False,
                "message": res["message"]}
    if status == "static_error":
        return {**out, "category": "static", "static_ok": False, "ran": False, "passed": False,
                "message": res["message"]}
    outputs, err = res["outputs"], res["error"]
    for i, got in enumerate(outputs):
        if not same(got, expected[i]):
            kind, label, args = tests[i]
            return {**out, "category": "wrong_output", "static_ok": True, "ran": err is None, "passed": False,
                    "message": f"wrong output on {label}",
                    "failing": {"kind": kind, "label": label, "input": args,
                                "expected": expected[i], "got": got}}
    if err is not None:
        kind, label, args = tests[err["index"]]
        return {**out, "category": "runtime", "static_ok": True, "ran": False, "passed": False,
                "message": err["message"], "failing": {"kind": kind, "label": label, "input": args}}
    return {**out, "category": "pass", "static_ok": True, "ran": True, "passed": True, "message": ""}


def score_reply(task_id, condition, text):
    code, declined = extract(text, condition)
    if code is None:
        cat = "declined" if declined else "extraction"
        return code, {"category": cat, "static_ok": False, "ran": False, "passed": False,
                      "message": "answered CANNOT_EXPRESS" if declined else "no code block in the reply"}
    return code, score_code(task_id, condition, code)


def feedback(result, condition):
    """The repair message sent after a failed attempt. Edge-case inputs may be shown; random test
    inputs never are, so the hidden tests stay hidden."""
    lang = {"chimni": "chimni", "python": "python", "pandas": "python", "sql": "sql"}[condition]
    fix = f"Fix it and reply with the complete corrected solution in one ```{lang} code block."
    cat, msg, failing = result["category"], result.get("message", ""), result.get("failing")
    if cat == "extraction":
        return f"Your reply did not contain a ```{lang} code block. Reply with the complete solution in one."
    if cat == "declined":
        return f"Please attempt a solution. Reply with the complete solution in one ```{lang} code block."
    if cat == "timeout":
        return f"Your solution did not finish in time. {fix}"
    if cat == "static":
        return f"Your solution was rejected before it ran:\n\n{msg[:800]}\n\n{fix}"
    shown = failing and failing["kind"] == "edge"
    where = f" on this input:\n\n{short(failing['input'], 800)}" if shown else " on a hidden test input."
    if cat == "runtime":
        return f"Your solution failed while running{where}\n\nError: {msg[:800]}\n\n{fix}"
    if shown:
        return (f"Your solution returned a wrong result on this input:\n\n{short(failing['input'], 800)}\n\n"
                f"Expected: {short(failing['expected'], 400)}\nGot: {short(failing['got'], 400)}\n\n{fix}")
    return f"Your solution returned a wrong result on a hidden test input. {fix}"
