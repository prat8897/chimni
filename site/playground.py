"""Glue between the playground page and the interpreter.

Runs in the browser under Pyodide, and at build time (site/build.py) to pre-render
each example's output so the page shows something before Python has loaded.
"""
import json

import chimni


def run(src, inputs_json):
    """Compile and run `src` on a JSON object of inputs. Always returns a JSON string."""
    out = {"ok": False, "rows": [], "trace": []}
    try:
        prog = chimni.compile_source(src)
    except chimni.LangError as e:
        out.update(stage="grammar", error=str(e), row=e.row, col=e.col)
        return json.dumps(out)
    out["rows"] = [[st.text for st in row] for row in prog.rows]
    out["sig"] = prog.sig_text
    try:
        args = json.loads(inputs_json)
    except ValueError as e:
        out.update(stage="inputs", error=f"inputs are not valid JSON: {e}")
        return json.dumps(out)
    if not isinstance(args, dict):
        out.update(stage="inputs", error='inputs must be a JSON object, like {"orders": [...], "min_total": 100}')
        return json.dumps(out)
    log = []
    try:
        result = prog.run(args, trace=log)
    except chimni.LangError as e:
        out.update(stage="run", error=str(e), row=e.row, col=e.col)
    else:
        out.update(ok=True, result=repr(result))
    for line in log:
        cell, value = line.split(" -> ", 1)
        r, c = cell.split()[0][1:].split("c")
        out["trace"].append({"r": int(r), "c": int(c), "out": value})
    return json.dumps(out)
