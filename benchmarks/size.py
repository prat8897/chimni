#!/usr/bin/env python3
"""How big is each example in plain Python, in its idiomatic pandas / SQL / jq form, and in Chimni?

Counts only code: comments and blank lines are dropped everywhere, and every column's
characters are counted with whitespace squeezed to single spaces (Chimni pads cells to
line up columns; Python indents; SQL wraps clauses - none of that should count).

    python benchmarks/size.py            # text table
    python benchmarks/size.py --md       # markdown table (used in the README)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
COMMENT = {".py": "#", ".sql": "--", ".jq": "#", ".chimni": "--"}
LANG = {".py": "pandas", ".sql": "SQL", ".jq": "jq"}


def code_only(path):
    prefix = COMMENT[path.suffix]
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith(prefix):
            continue
        lines.append(raw.rstrip())
    return "\n".join(lines)


def squeezed(code):
    return " ".join(code.split())


def alternative_path(stem):
    (path,) = list((EX / "compare").glob(stem + ".*"))
    return path


def measure():
    """One dict per example: lines and squeezed characters for py, alt and chimni."""
    rows = []
    for c in sorted(EX.glob("*.chimni")):
        alt = alternative_path(c.stem)
        codes = {"py": code_only(EX / "python" / (c.stem + ".py")), "alt": code_only(alt), "chimni": code_only(c)}
        row = {"example": c.stem, "alt_lang": LANG[alt.suffix]}
        for k, code in codes.items():
            row[k + "_lines"] = len(code.splitlines())
            row[k + "_chars"] = len(squeezed(code))
        rows.append(row)
    return rows


def main():
    md = "--md" in sys.argv
    data = measure()
    keys = ["py_lines", "alt_lines", "chimni_lines", "py_chars", "alt_chars", "chimni_chars"]
    head = ["example", "alt", "py lines", "alt lines", "chimni lines", "py chars", "alt chars", "chimni chars"]
    rows = [[d["example"], d["alt_lang"]] + [d[k] for k in keys] for d in data]
    rows.append(["**total**", ""] + [sum(d[k] for d in data) for k in keys])

    if md:
        print("| " + " | ".join(head) + " |")
        print("|" + "|".join(["---", "---"] + ["---:"] * len(keys)) + "|")
        for r in rows:
            print("| " + " | ".join(str(x) for x in r) + " |")
        print("\nCharacters are counted with whitespace squeezed to single spaces; comments and blank lines are dropped.")
    else:
        w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
        print("  ".join(h.ljust(w[i]) for i, h in enumerate(head)))
        for r in rows:
            print("  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))


if __name__ == "__main__":
    main()
