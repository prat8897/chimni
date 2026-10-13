#!/usr/bin/env python3
"""How big is each example in Python vs Chimni?

Counts only code: comments and blank lines are dropped on both sides.
If `tiktoken` is installed, a token column is added (cl100k_base) - that is the
number the "token efficiency" idea actually needs, and nobody has measured it
properly yet. See CONTRIBUTING.md.

    python benchmarks/size.py            # text table
    python benchmarks/size.py --md       # markdown table (used in the README)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"


def code_only(path, comment_prefix):
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith(comment_prefix):
            continue
        lines.append(raw.rstrip())
    return "\n".join(lines)


def tokenizer():
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return lambda s: len(enc.encode(s))
    except Exception:
        return None


def main():
    md = "--md" in sys.argv
    count_tokens = tokenizer()
    rows = []
    for c in sorted(EX.glob("*.chimni")):
        py = code_only(EX / "python" / (c.stem + ".py"), "#")
        ch = code_only(c, "--")
        # a chimni program's whitespace is alignment padding; compare it squeezed too
        ch_sq = " ".join(ch.split())
        row = [c.stem, len(py.splitlines()), len(ch.splitlines()), len(py), len(ch_sq)]
        if count_tokens:
            row += [count_tokens(py), count_tokens(ch)]
        rows.append(row)

    head = ["example", "py lines", "chimni lines", "py chars", "chimni chars*"]
    if count_tokens:
        head += ["py tokens", "chimni tokens"]
    tot = ["**total**"] + [sum(r[i] for r in rows) for i in range(1, len(head))]
    rows.append(tot)

    if md:
        print("| " + " | ".join(head) + " |")
        print("|" + "|".join(["---"] + ["---:"] * (len(head) - 1)) + "|")
        for r in rows:
            print("| " + " | ".join(str(x) for x in r) + " |")
        print("\n\\* whitespace squeezed to single spaces (Chimni pads cells to line up columns).")
    else:
        w = [max(len(str(r[i])) for r in rows + [head]) for i in range(len(head))]
        print("  ".join(h.ljust(w[i]) for i, h in enumerate(head)))
        for r in rows:
            print("  ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))


if __name__ == "__main__":
    main()
