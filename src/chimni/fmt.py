"""`chimni fmt`: line cells up into columns.

Only whitespace changes. A cell's column is its position in its row, so alignment never changes what a program
means; it just makes the columns, and therefore the ties, visible.
"""
from .interpreter import GrammarError

GAP = 2


def split_row(line):
    """Split a grid row into (cells, trailing comment or ''), using the interpreter's rules for brackets and quotes."""
    cells, cur, depth, inq, start = [], "", 0, False, 0
    for i, ch in enumerate(line):
        if ch == '"':
            inq = not inq
        if not inq:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch.isspace() and depth == 0:
                if cur:
                    if cur == "--":
                        return cells, line[start:].rstrip()
                    cells.append(cur)
                    cur = ""
                continue
        if not cur:
            start = i
        cur += ch
    if depth != 0 or inq:
        raise GrammarError("unbalanced bracket or quote")
    if cur == "--":
        return cells, "--"
    if cur:
        cells.append(cur)
    return cells, ""


def format_source(src):
    lines = src.splitlines()
    kinds, seen_sig = [], False
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("--"):
            kinds.append(("keep", s))
        elif not seen_sig and s.startswith("$"):
            seen_sig = True
            kinds.append(("keep", s))
        else:
            kinds.append(("row", split_row(s)))
    widths = []
    for kind, val in kinds:
        if kind == "row":
            for c, cell in enumerate(val[0]):
                if c == len(widths):
                    widths.append(0)
                widths[c] = max(widths[c], len(cell))
    out = []
    for kind, val in kinds:
        if kind == "keep":
            out.append(val)
            continue
        cells, comment = val
        parts = [cell.ljust(widths[c] + GAP) for c, cell in enumerate(cells)]
        line = "".join(parts).rstrip()
        if comment:
            line = (line + " " * GAP + comment) if line else comment
        out.append(line)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out) + "\n"
