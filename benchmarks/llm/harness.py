"""Runs ONE generated solution over a list of inputs. Executed in a sandboxed child process.

    python -I harness.py job.json  ->  prints one JSON object on stdout

Standalone on purpose: it imports nothing from the benchmark package, so the child process
needs only the standard library (plus pandas for the pandas condition, chimni for chimni).

Result shapes:
  {"status": "static_error", "message": ...}     rejected before running on any input
  {"status": "ok", "outputs": [...], "error": null | {"index": i, "message": ...}}
                                                  outputs[i] for every input before the first runtime error
"""
import json
import sys
import traceback


def plain(v):
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    if hasattr(v, "item") and type(v).__module__.startswith("numpy"):
        return v.item()
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return {"__unserializable__": f"{type(v).__module__}.{type(v).__name__}"}


def py_error(e):
    msg = f"{type(e).__name__}: {e}"
    lines = [f.lineno for f in traceback.extract_tb(e.__traceback__) if f.filename == "<solution>"]
    return msg + (f" (line {lines[-1]} of your solution)" if lines else "")


# ---------------------------------------------------------------- python
def prepare_python(code):
    try:
        compiled = compile(code, "<solution>", "exec")
    except SyntaxError as e:
        return None, f"SyntaxError: {e.msg} (line {e.lineno} of your solution)"
    ns = {"__name__": "solution"}
    try:
        exec(compiled, ns)
    except BaseException as e:   # noqa: BLE001 - anything the module does at import time
        return ("load_error", py_error(e)), None
    fn = ns.get("solve")
    if not callable(fn):
        return ("load_error", "NameError: the solution does not define a function named solve"), None
    return fn, None


# ---------------------------------------------------------------- chimni
def prepare_chimni(code, chimni_src):
    sys.path.insert(0, chimni_src)
    import chimni
    try:
        prog = chimni.compile_source(code)
    except chimni.LangError as e:
        return None, str(e)

    def run(**args):
        return prog.run(args)
    return run, None


def chimni_error(e):
    return str(e) if type(e).__module__.startswith("chimni") else py_error(e)


# ------------------------------------------------------------------- sql
def sql_db(args, tables):
    import sqlite3
    db = sqlite3.connect(":memory:")
    for name, cols in tables.items():
        if isinstance(cols, str):                       # a list of plain values, one column
            db.execute(f'CREATE TABLE "{name}" ("{cols}")')
            db.executemany(f'INSERT INTO "{name}" VALUES (?)', [(v,) for v in args[name]])
        else:
            db.execute(f'CREATE TABLE "{name}" ({", ".join(chr(34) + c + chr(34) for c in cols)})')
            db.executemany(f'INSERT INTO "{name}" VALUES ({", ".join("?" * len(cols))})',
                           [tuple(row[c] for c in cols) for row in args[name]])
    params = {k: v for k, v in args.items() if k not in tables}
    return db, params


def sql_shape(rows, kind):
    if kind == "scalar":
        return rows[0][0] if rows else None
    if kind == "column":
        return [r[0] for r in rows]
    return [list(r) for r in rows]


def prepare_sql(code, job, first_args):
    import sqlite3
    stmt = code.strip()
    db, params = sql_db(first_args, job["tables"])
    try:
        db.execute("EXPLAIN " + stmt, params)       # compiles the statement without running it
    except (sqlite3.Error, sqlite3.Warning, ValueError) as e:
        return None, f"{type(e).__name__}: {e}"

    def run(**args):
        db2, params2 = sql_db(args, job["tables"])
        return sql_shape(db2.execute(stmt, params2).fetchall(), job["sql_output"])
    return run, None


# ------------------------------------------------------------------ main
def main():
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    lang, code, inputs = job["lang"], job["code"], job["inputs"]
    if lang in ("python", "pandas"):
        fn, static = prepare_python(code)
    elif lang == "chimni":
        fn, static = prepare_chimni(code, job["chimni_src"])
    elif lang == "sql":
        fn, static = prepare_sql(code, job, inputs[0] if inputs else {})
    else:
        raise SystemExit(f"unknown language {lang}")
    if static is not None:
        print(json.dumps({"status": "static_error", "message": static}))
        return
    if isinstance(fn, tuple):                        # python module failed while loading
        print(json.dumps({"status": "ok", "outputs": [], "error": {"index": 0, "message": fn[1]}}))
        return
    outputs, error = [], None
    for i, args in enumerate(inputs):
        try:
            outputs.append(plain(fn(**args)))
        except BaseException as e:  # noqa: BLE001
            msg = chimni_error(e) if lang == "chimni" else (
                f"{type(e).__name__}: {e}" if lang == "sql" else py_error(e))
            error = {"index": i, "message": msg}
            break
    print(json.dumps({"status": "ok", "outputs": outputs, "error": error}))


if __name__ == "__main__":
    main()
