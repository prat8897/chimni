"""Command line: `chimni program.chimni '{"input": ...}' [--trace] [--json]`."""
import argparse
import json
import sys

from . import __version__
from .interpreter import LangError, load


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="chimni",
        description="Run a Chimni program. With no inputs, just check that it is well-formed.",
    )
    ap.add_argument("file", help="a .chimni program")
    ap.add_argument("args", nargs="?", help="inputs as a JSON object, or @file.json")
    ap.add_argument("--trace", action="store_true", help="show every cell's output, row by row")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    ap.add_argument("--version", action="version", version=f"chimni {__version__}")
    ns = ap.parse_args(argv)
    try:
        prog = load(ns.file)
        if ns.args is None:
            print(f"ok  {prog.sig_text}   ({len(prog.rows)} row(s))")
            return 0
        raw = open(ns.args[1:], encoding="utf-8").read() if ns.args.startswith("@") else ns.args
        log = [] if ns.trace else None
        result = prog.run(json.loads(raw), trace=log)
        if log:
            print("\n".join(log))
        print(json.dumps(result) if ns.json else repr(result))
        return 0
    except LangError as e:
        print(e, file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
