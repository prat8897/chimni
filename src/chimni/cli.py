"""Command line.

    chimni PROGRAM [DATA ...]          run a program on JSON or CSV data
    chimni fmt [-w | --check] [FILE ...]

PROGRAM is a .chimni file or the program text itself. Inline programs may leave out the signature: inputs are
the names used in @cells, [brackets] and ties, and each ^ fills one output.

DATA is a .json/.csv file, `name=file`, a JSON literal, or @file.json. With no DATA, standard input is read.

    cat orders.json | chimni '@orders  #(customer)  +s(amount)  ~\\(total)  ^'
    chimni '@orders  ?(amount)>[limit]  ^' orders.csv --arg limit=100
    chimni examples/01_big_spenders.chimni @examples/inputs/01_big_spenders.json --trace
"""
import argparse
import csv
import io
import json
import os
import re
import stat
import sys

from . import __version__
from .fmt import format_source, split_row
from .interpreter import LangError, compile_source

NUMBER = re.compile(r"-?\d+(\.\d+)?([eE][-+]?\d+)?$")
IDENT = re.compile(r"[A-Za-z_]\w*$")


# --------------------------------------------------------------- program
def infer_signature(src):
    """Prepend `$[inputs]{out|none,...}` to a program written without a signature."""
    code = [ln for ln in src.splitlines() if ln.strip() and not ln.strip().startswith("--")]
    if not code or code[0].strip().startswith("$"):
        return src
    inputs, emits = [], 0

    def add(name):
        if name not in inputs:
            inputs.append(name)
    for line in code:
        for cell in split_row(line.strip())[0]:
            if cell.startswith("@"):
                m = re.match(r"@(\w+)", cell)
                if m:
                    add(m.group(1))
            elif cell.startswith("^"):
                emits += 1
            elif "'" in cell and cell[0] in "'0123456789":
                for tok in re.findall(r"[A-Za-z_]\w*", cell):
                    add(tok)
            for body in re.findall(r"\[([^\]]*)\]", cell):
                for part in body.split(","):
                    part = part.split(":", 1)[0].strip()
                    if IDENT.match(part) and part != "_":
                        add(part)
    outs = ["out|none"] if emits <= 1 else [f"out{i}|none" for i in range(1, emits + 1)]
    return f"$[{','.join(inputs)}]{{{','.join(outs)}}}\n{src}"


def load_program(text):
    if os.path.isfile(text):
        with open(text, encoding="utf-8") as f:
            return compile_source(f.read())
    return compile_source(infer_signature(text))


# ------------------------------------------------------------------ data
def scalar(s):
    if s == "":
        return None
    if NUMBER.match(s):
        return float(s) if any(c in s for c in ".eE") else int(s)
    return s


def parse_csv(text, delimiter=","):
    return [{k: scalar(v) for k, v in row.items()} for row in csv.DictReader(io.StringIO(text), delimiter=delimiter)]


def parse_data(text, kind=None):
    if kind == "csv":
        return parse_csv(text)
    if kind == "tsv":
        return parse_csv(text, "\t")
    if kind == "jsonl":
        return [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if kind == "json":
            raise
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if lines and all(ln.lstrip().startswith(("{", "[")) for ln in lines):
            return [json.loads(ln) for ln in lines]
        return parse_csv(text)


def read_source(arg, force_csv):
    """-> (name or None, value, from_file: bool)"""
    name = None
    m = re.match(r"([A-Za-z_]\w*)=(.+)$", arg)
    if m and os.path.isfile(m.group(2)):
        name, arg = m.group(1), m.group(2)
    path = arg[1:] if arg.startswith("@") else arg
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        with open(path, encoding="utf-8") as f:
            value = parse_data(f.read(), "csv" if force_csv else ext if ext in ("csv", "tsv", "jsonl", "json") else None)
        stem = os.path.splitext(os.path.basename(path))[0]
        return name or (stem if IDENT.match(stem) else None), value, True
    if arg.startswith("@"):
        raise OSError(f"no such file: {path}")
    return name, json.loads(arg), False


def bind(params, sources, args):
    """Match data sources to program inputs. Returns the kwargs for Program.run."""
    bound = dict(args)
    free = [s for s in sources if s[0] is None or s[0] not in params]
    for name, value, _ in sources:
        if name in params:
            bound[name] = value
    rest = [p for p in params if p not in bound]
    # one JSON object holding every remaining input by name (the classic form)
    if len(free) == 1 and isinstance(free[0][1], dict) and rest and all(p in free[0][1] for p in rest):
        extra = [k for k in free[0][1] if k not in params]
        bound.update({k: v for k, v in free[0][1].items() if k in params})
        if extra and not free[0][2]:
            bound.update({k: free[0][1][k] for k in extra})       # let Program.run name the unknown inputs
        return bound
    if len(free) > len(rest):
        raise LangError(f"got {len(sources)} data source(s) for input(s) {', '.join(params) or 'none'}")
    for p, (_, value, _) in zip(rest, free):
        bound[p] = value
    return bound


def stdin_has_data():
    """True when standard input is a pipe or a redirected file (not a terminal, not /dev/null)."""
    try:
        mode = os.fstat(sys.stdin.fileno()).st_mode
    except (OSError, ValueError, AttributeError):
        return False
    return stat.S_ISFIFO(mode) or stat.S_ISREG(mode)


# ---------------------------------------------------------------- output
def plain(v):
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    return v


def to_json(result, compact):
    flat = not isinstance(result, (list, tuple)) or not any(isinstance(x, (list, tuple, dict)) for x in result)
    if compact or flat:
        return json.dumps(plain(result), separators=(",", ":") if compact else None)
    return "[\n" + ",\n".join("  " + json.dumps(plain(x)) for x in result) + "\n]"


def to_csv(result):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    rows = result if isinstance(result, list) else [result]
    if rows and all(isinstance(r, dict) for r in rows):
        head = list(rows[0])
        w.writerow(head)
        for r in rows:
            w.writerow([r.get(k) for k in head])
    else:
        for r in rows:
            w.writerow(list(r) if isinstance(r, (list, tuple)) else [r])
    return out.getvalue().rstrip("\n")


# ------------------------------------------------------------------ main
def run_main(argv):
    ap = argparse.ArgumentParser(prog="chimni", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("program", help="a .chimni file, or the program text")
    ap.add_argument("data", nargs="*", help="JSON/CSV files, name=file, a JSON literal, or @file.json")
    ap.add_argument("--arg", action="append", default=[], metavar="NAME=VALUE",
                    help="set one input (VALUE is read as JSON, or else as text)")
    ap.add_argument("--csv", action="store_true", help="read the data as CSV")
    ap.add_argument("-o", "--output", choices=["json", "csv", "repr"], default="json")
    ap.add_argument("-c", "--compact", action="store_true", help="JSON on one line")
    ap.add_argument("--json", action="store_true", help=argparse.SUPPRESS)       # the default; kept for old scripts
    ap.add_argument("--trace", action="store_true", help="print every cell's output to stderr")
    ap.add_argument("--check", action="store_true", help="only check that the program is well-formed")
    ap.add_argument("--version", action="version", version=f"chimni {__version__}")
    ns = ap.parse_args(argv)
    try:
        prog = load_program(ns.program)
        stdin_data = not ns.data and not ns.check and stdin_has_data()
        if ns.check or (not ns.data and not stdin_data and not ns.arg):
            if not ns.check and not os.path.isfile(ns.program):
                raise LangError("no data: pass a file, a JSON literal, or pipe data into chimni")
            print(f"ok  {prog.sig_text}   ({len(prog.rows)} row(s))")
            return 0
        sources = [read_source(d, ns.csv) for d in ns.data]
        if stdin_data:
            sources.append((None, parse_data(sys.stdin.read(), "csv" if ns.csv else None), True))
        args = {}
        for a in ns.arg:
            k, _, v = a.partition("=")
            try:
                args[k] = json.loads(v)
            except json.JSONDecodeError:
                args[k] = v
        log = [] if ns.trace else None
        result = prog.run(bind(prog.params, sources, args), trace=log)
        if log:
            print("\n".join(log), file=sys.stderr)
        if ns.output == "repr":
            print(repr(result))
        elif ns.output == "csv":
            print(to_csv(plain(result)))
        else:
            print(to_json(result, ns.compact))
        return 0
    except LangError as e:
        print(e, file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError, csv.Error) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


def fmt_main(argv):
    ap = argparse.ArgumentParser(prog="chimni fmt", description="Line cells up into columns. Only whitespace changes.")
    ap.add_argument("files", nargs="*", help="files to format (default: standard input)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("-w", "--write", action="store_true", help="rewrite the files in place")
    g.add_argument("--check", action="store_true", help="exit 1 if any file is not formatted")
    ns = ap.parse_args(argv)
    try:
        if not ns.files:
            sys.stdout.write(format_source(sys.stdin.read()))
            return 0
        unformatted = []
        for path in ns.files:
            with open(path, encoding="utf-8") as f:
                src = f.read()
            out = format_source(src)
            if ns.check:
                if out != src:
                    unformatted.append(path)
            elif ns.write:
                if out != src:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(out)
            else:
                sys.stdout.write(out)
        for path in unformatted:
            print(f"would reformat {path}", file=sys.stderr)
        return 1 if unformatted else 0
    except LangError as e:
        print(e, file=sys.stderr)
        return 1
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "fmt":
        return fmt_main(argv[1:])
    return run_main(argv)
