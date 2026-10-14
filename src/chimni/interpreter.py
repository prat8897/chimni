#!/usr/bin/env python3
"""Chimni interpreter: parser, static checker and executor.

A program is a signature line plus rows of cells.
  - a cell consumes the output of the cell on its left (same row)
  - a new row is an independent chain
  - `'` ties read the cell above in the same column (joins without names)
  - `^` emits a row into the next output slot of the signature

Language reference: docs/SPEC.md
"""
import operator
import re


# ----------------------------------------------------------------- errors
class LangError(Exception):
    kind = "error"

    def __init__(self, msg, row=None, col=None):
        super().__init__(msg)
        self.msg, self.row, self.col = msg, row, col

    def __str__(self):
        loc = f" at row {self.row}, col {self.col}" if self.row is not None else ""
        return f"{self.kind}{loc}: {self.msg}"


class GrammarError(LangError):
    kind = "grammar error"


class RunError(LangError):
    kind = "run error"


# ------------------------------------------------------------- data model
class Record(dict):
    """A dict that knows which field is its 'value' (set by aggregates)."""
    __slots__ = ("vf",)

    def __init__(self, data=(), vf=None):
        super().__init__(data)
        self.vf = vf

    def with_value(self, v):
        r = Record(self, self.vf)
        r[self.vf] = v
        return r


class Grouped:
    """Output of #(k): needs an aggregate before anything else can use it."""

    def __init__(self, keyname, groups):
        self.keyname, self.groups = keyname, groups  # groups: [(key, [items])]


class _Empty:
    def __repr__(self):
        return "."


EMPTY = _Empty()

CMP = {">": operator.gt, "<": operator.lt, ">=": operator.ge,
       "<=": operator.le, "=": operator.eq, "!=": operator.ne}
ARITH = {"+": operator.add, "-": operator.sub,
         "*": operator.mul, "/": operator.truediv}
AGG_NAME = {"s": "total", "n": "count", "a": "avg", "r": "run", "m": None, "i": None}


def plain(v):
    if isinstance(v, dict):
        return dict(v)
    if isinstance(v, list):
        return [plain(x) for x in v]
    return v


def short(v, w=72):
    if isinstance(v, Grouped):
        s = f"groups({len(v.groups)}) by {v.keyname}: " + \
            ", ".join(f"{k!r}x{len(it)}" for k, it in v.groups[:4])
    elif isinstance(v, list):
        s = f"[{len(v)}] {plain(v[:3])!r}"
    else:
        s = repr(plain(v))
    return s if len(s) <= w else s[: w - 1] + "…"


# ---------------------------------------------------------------- helpers
def value_of(item):
    """The default 'value' of an item: the scalar itself, or an aggregate's field."""
    if isinstance(item, Record) and item.vf is not None:
        return item[item.vf]
    if isinstance(item, dict):
        raise RunError(f"{short(item)} has no default value here; name a field, e.g. (amount)")
    return item


def get_field(item, f):
    if isinstance(item, dict):
        if f in item:
            return item[f]
        raise RunError(f"no field '{f}' (item has: {', '.join(map(str, item))})")
    raise RunError(f"cannot read field '{f}' of {short(item)}")


def val(item, f):
    return get_field(item, f) if f else value_of(item)


def key_of(item, f):
    k = get_field(item, f) if f else item
    try:
        hash(k)
    except TypeError:
        raise RunError(f"cannot group/dedupe by {short(k)}; name a field, e.g. (customer)")
    return k


def need_list(v, what):
    if isinstance(v, Grouped):
        raise RunError(f"{what} needs a stream but got un-aggregated groups; "
                       f"add an aggregate (+s(..), +n, ...) after the #")
    if not isinstance(v, list):
        raise RunError(f"{what} needs a stream (list) but got {short(v)}")
    return v


def pick_fields(item, fs):
    if len(fs) == 1:
        return get_field(item, fs[0])
    return tuple(get_field(item, f) for f in fs)


def apply_pick(v, fs):
    if v is None:
        return None
    if isinstance(v, list):
        return [pick_fields(i, fs) for i in v]
    if isinstance(v, dict):
        return pick_fields(v, fs)
    raise RunError(f"cannot pick field(s) {', '.join(fs)} from {short(v)}")


def item_op(op, x, y):
    if x is None or y is None:
        return None
    vx, vy = value_of(x), value_of(y)
    try:
        r = ARITH[op](vx, vy)
    except ZeroDivisionError:
        raise RunError("division by zero")
    except TypeError:
        raise RunError(f"cannot compute {short(vx)} {op} {short(vy)}")
    if isinstance(x, Record) and x.vf is not None:
        return x.with_value(r)
    if isinstance(y, Record) and y.vf is not None:
        return y.with_value(r)
    return r


def record_keys(stream):
    """For a stream of aggregate records, each item's key (its fields other than the value); otherwise None."""
    if not stream or not all(isinstance(x, Record) and x.vf is not None for x in stream):
        return None
    names = [k for k in stream[0] if k != stream[0].vf]
    if any([k for k in x if k != x.vf] != names for x in stream):
        return None
    return [tuple((k, x[k]) for k in names) for x in stream]


def align_by_key(a, b):
    """Two keyed streams pair up by key, in the left stream's order. Different keys are an error."""
    ka, kb = record_keys(a), record_keys(b)
    if ka is None or kb is None or ka == kb:
        return b
    if [[k for k, _ in key] for key in ka[:1]] != [[k for k, _ in key] for key in kb[:1]]:
        raise RunError(f"cannot pair rows keyed by {', '.join(k for k, _ in ka[0])} "
                       f"with rows keyed by {', '.join(k for k, _ in kb[0])}")
    index = dict(zip(kb, b))
    if len(index) != len(kb) or len(set(ka)) != len(ka):
        raise RunError("a key appears twice in a row, so the rows cannot be paired by key")
    if set(ka) != set(index):
        show = lambda keys: ", ".join(" ".join(f"{k}={v!r}" for k, v in key) for key in keys[:3])
        left = [k for k in ka if k not in index]
        right = [k for k in kb if k not in set(ka)]
        raise RunError(f"the streams being combined have different keys: {show(left)} only on the left of the "
                       f"operator, {show(right)} only on the right")
    return [index[k] for k in ka]


def binop(op, a, b):
    if isinstance(a, Grouped) or isinstance(b, Grouped):
        raise RunError("aggregate the groups before doing arithmetic on them")
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            raise RunError(f"streams differ in length ({len(a)} vs {len(b)})")
        b = align_by_key(a, b)
        return [item_op(op, x, y) for x, y in zip(a, b)]
    if isinstance(a, list):
        return [item_op(op, x, b) for x in a]
    if isinstance(b, list):
        return [item_op(op, a, y) for y in b]
    return item_op(op, a, b)


def eval_expr(vals, ops):
    vs, os_ = [vals[0]], []
    for op, v in zip(ops, vals[1:]):          # * and / bind tighter
        if op in "*/":
            vs[-1] = binop(op, vs[-1], v)
        else:
            os_.append(op)
            vs.append(v)
    res = vs[0]
    for op, v in zip(os_, vs[1:]):
        res = binop(op, res, v)
    return res


def agg_items(op, f, items):
    if op == "n":
        return len(items)
    if op == "s":
        return sum(val(it, f) for it in items)
    if op == "a":
        return sum(val(it, f) for it in items) / len(items) if items else None
    if op == "m":
        return max(items, key=lambda it: val(it, f)) if items else None
    if op == "i":
        return min(items, key=lambda it: val(it, f)) if items else None
    raise AssertionError(op)


def aggregate(op, f, name, inp):
    if op == "r":
        out, run = [], 0
        for i, it in enumerate(need_list(inp, "+r")):
            run += val(it, f)
            out.append(Record({"i": i, name: run}, name))
        return out
    if isinstance(inp, Grouped):
        recs = []
        for k, items in inp.groups:
            res = agg_items(op, f, items)
            recs.append(res if op in "mi" else Record({inp.keyname: k, name: res}, name))
        return recs
    return agg_items(op, f, need_list(inp, f"+{op}"))


# ---------------------------------------------------------------- parsing
NUM = re.compile(r"-?\d+(?:\.\d+)?$")


def parse_operand(t, params):
    t = t.strip()
    if NUM.match(t):
        return ("c", float(t) if "." in t else int(t))
    if len(t) >= 2 and t[0] == t[-1] == '"':
        return ("c", t[1:-1])
    if t in params:
        return ("p", t)
    raise GrammarError(f"unknown name `{t}` (not a number, \"string\" or input; "
                       f"inputs are: {', '.join(params) or 'none'})")


def parse_label(t):
    t = t.strip()
    if NUM.match(t):
        return float(t) if "." in t else int(t)
    if len(t) >= 2 and t[0] == t[-1] == '"':
        return t[1:-1]
    return t


def ev(op, args):
    return op[1] if op[0] == "c" else args[op[1]]


class Stage:
    def __init__(self, kind, text, **kw):
        self.kind, self.text = kind, text
        self.__dict__.update(kw)


def parse_stage(t, params):
    if t == ".":
        return Stage("empty", t)
    if "'" in t and t[0] in "'0123456789":
        toks = re.findall(r"'+|\d+(?:\.\d+)?|[A-Za-z_]\w*|[-+*/]", t)
        if "".join(toks) != t or len(toks) % 2 == 0:
            raise GrammarError(f"bad tie expression `{t}`")
        operands, ops = [], []
        for i, tk in enumerate(toks):
            if i % 2 == 0:
                if tk[0] == "'":
                    operands.append(("tie", len(tk)))
                else:
                    operands.append(parse_operand(tk, params))
            elif tk in "+-*/":
                ops.append(tk)
            else:
                raise GrammarError(f"bad tie expression `{t}`: expected an operator, got `{tk}`")
        return Stage("tie", t, operands=operands, ops=ops)
    c = t[0]
    if c == "@":
        m = re.fullmatch(r"@(\w+)(?:\((\w+)=(\w+)\))?", t)
        if not m:
            raise GrammarError(f"bad source `{t}`; expected @name or @name(theirField=myField)")
        name, a, b = m.groups()
        if name not in params:
            raise GrammarError(f"`{t}`: no input named '{name}' (inputs: {', '.join(params) or 'none'})")
        return Stage("source", t, name=name, join=(a, b) if a else None)
    if c in "#%":
        m = re.fullmatch(r"[#%]\((\w*)\)", t)
        if not m:
            raise GrammarError(f"bad `{t}`; expected {c}(field) or {c}()")
        return Stage("group" if c == "#" else "unique", t, f=m.group(1))
    if c == "?":
        m = re.fullmatch(r"\?(?:\((\w*)\))?(>=|<=|!=|>|<|=)\[(.*)\]", t)
        if not m:
            raise GrammarError(f"bad filter `{t}`; expected ?(field)>[value] or ?>[value]")
        f, op, body = m.group(1) or "", m.group(2), m.group(3)
        if ":" in body:  # ladder: ?>=[90:A, 75:B, _:C]
            rungs, default = [], None
            for part in body.split(","):
                if ":" not in part:
                    raise GrammarError(f"bad ladder rung `{part.strip()}` in `{t}`; expected threshold:label")
                thr, label = part.split(":", 1)
                if thr.strip() == "_":
                    default = parse_label(label)
                else:
                    rungs.append((parse_operand(thr, params), parse_label(label)))
            return Stage("ladder", t, f=f, op=op, rungs=rungs, default=default)
        return Stage("filter", t, f=f, op=op, rhs=parse_operand(body, params))
    if c == "*":
        m = re.fullmatch(r"\*\((\w+(?:,\w+)*)\)", t)
        if not m:
            raise GrammarError(f"bad pick `{t}`; expected *(field) or *(a,b)")
        return Stage("pick", t, fs=m.group(1).split(","))
    if c == "_":
        m = re.fullmatch(r"_([lu])", t)
        if not m:
            raise GrammarError(f"bad `{t}`; expected _l (lowercase) or _u (uppercase)")
        return Stage("case", t, mode=m.group(1))
    if c == ";":
        if t != ";w":
            raise GrammarError(f"bad `{t}`; only ;w (split into words) exists")
        return Stage("words", t)
    if c == "+":
        m = re.fullmatch(r"\+([snamir])(?:\((\w*)\))?(?::(\w+))?", t)
        if not m:
            raise GrammarError(f"bad aggregate `{t}`; expected +s +n +a +m +i +r, e.g. +s(amount)")
        op = m.group(1)
        return Stage("agg", t, op=op, f=m.group(2) or "", name=m.group(3) or AGG_NAME[op])
    if c == "~":
        m = re.fullmatch(r"~([/\\])(?:\((\w*)\))?", t)
        if not m:
            raise GrammarError(f"bad sort `{t}`; expected ~/ or ~\\ optionally followed by (field)")
        return Stage("sort", t, desc=m.group(1) == "\\", f=m.group(2) or "")
    if c == "^":
        m = re.fullmatch(r"\^(?:\[(\w+)\])?(?:\((\w+(?:,\w+)*)\))?", t)
        if not m:
            raise GrammarError(f"bad emit `{t}`; expected ^, ^[n] or ^[n](field)")
        n = parse_operand(m.group(1), params) if m.group(1) else None
        return Stage("emit", t, n=n, one=(n == ("c", 1)),
                     fs=m.group(2).split(",") if m.group(2) else None)
    raise GrammarError(f"unknown symbol `{t}`")


def split_cells(line):
    cells, cur, depth, inq = [], "", 0, False
    for ch in line:
        if ch == '"':
            inq = not inq
        if not inq:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch.isspace() and depth == 0:
                if cur:
                    cells.append(cur)
                    cur = ""
                continue
        cur += ch
    if depth != 0 or inq:
        raise GrammarError("unbalanced bracket or quote")
    if cur:
        cells.append(cur)
    out = []
    for c in cells:          # a bare `--` cell starts a comment
        if c == "--":
            break
        out.append(c)
    return out


class Slot:
    def __init__(self, label, fields, nullable):
        self.label, self.fields, self.nullable = label, fields, nullable


def parse_sig(s):
    m = re.fullmatch(r"\$(\w*)\[([^\]]*)\]\{(.*)\}", re.sub(r"\s+", "", s))
    if not m:
        raise GrammarError("signature must look like $[inputs]{outputs}, e.g. $[orders,n]{(customer,total)}")
    name, ins, outs = m.groups()
    params = [p for p in ins.split(",") if p]
    for p in params:
        if not re.fullmatch(r"[A-Za-z_]\w*", p):
            raise GrammarError(f"bad input name `{p}`")
    parts, depth, cur = [], 0, ""
    for ch in outs:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        parts.append(cur)
    slots = []
    for p in parts:
        main, *alts = p.split("|")
        if any(a != "none" for a in alts):
            raise GrammarError(f"output `{p}`: the only alternative allowed is |none")
        t = re.fullmatch(r"\((\w+(?:,\w+)*)\)", main)
        if t:
            slots.append(Slot(main, t.group(1).split(","), bool(alts)))
        elif re.fullmatch(r"\w+", main):
            slots.append(Slot(main, None, bool(alts)))
        else:
            raise GrammarError(f"bad output `{p}`; expected name, (a,b) or either with |none")
    return name, params, slots


# ---------------------------------------------------------------- program
class Program:
    def __init__(self, name, params, slots, rows, sig_text):
        self.name, self.params, self.slots = name, params, slots
        self.rows, self.sig_text = rows, sig_text   # rows: [[Stage]]
        self._check()

    # static pass: catches missing inputs, bad ties, wrong number of outputs
    def _check(self):
        has = {}
        n_emit = 0
        for r, row in enumerate(self.rows):
            prev = False
            for c, st in enumerate(row):
                where = (r + 1, c + 1)
                if st.kind == "emit":
                    if not prev:
                        raise GrammarError(f"`{st.text}` has nothing to emit (column {c} is empty)", *where)
                    if c != len(row) - 1:
                        raise GrammarError("nothing may follow ^ in a row", r + 1, c + 2)
                    n_emit += 1
                    out = True
                elif st.kind == "empty":
                    out = prev
                elif st.kind == "source" and st.join is None:
                    out = True
                elif st.kind == "tie":
                    for o in st.operands:
                        if o[0] != "tie":
                            continue
                        rr = r - o[1]
                        if rr < 0:
                            raise GrammarError(f"`{st.text}` reaches {o[1]} row(s) up but only {r} exist above", *where)
                        if c >= len(self.rows[rr]) or not has.get((rr, c)):
                            raise GrammarError(f"`{st.text}` reads row {rr + 1}, col {c + 1}, which is empty", *where)
                    out = True
                else:
                    if not prev:
                        raise GrammarError(f"`{st.text}` has no input: the cell to its left (col {c}) is empty", *where)
                    out = True
                has[(r, c)] = out
                prev = out
        if n_emit != len(self.slots):
            raise GrammarError(f"signature declares {len(self.slots)} output(s) but the rows emit {n_emit} (^)")

    def __call__(self, *pos, **kw):
        if len(pos) > len(self.params):
            raise RunError(f"takes {len(self.params)} input(s), got {len(pos)}")
        args = dict(zip(self.params, pos))
        args.update(kw)
        return self.run(args)

    def run(self, args, trace=None):
        missing = [p for p in self.params if p not in args]
        extra = [a for a in args if a not in self.params]
        if missing:
            raise RunError(f"missing input(s): {', '.join(missing)}")
        if extra:
            raise RunError(f"unknown input(s): {', '.join(extra)} (declared: {', '.join(self.params)})")
        table, emitted, pos = {}, [], []
        for r, row in enumerate(self.rows):
            inp = EMPTY
            for c, st in enumerate(row):
                try:
                    out = self._exec(st, inp, args, table, r, c)
                except LangError as e:
                    if e.row is None:
                        e.row, e.col = r + 1, c + 1
                    raise
                except (TypeError, ValueError, KeyError, IndexError, AttributeError) as e:
                    raise RunError(f"{type(e).__name__}: {e}", r + 1, c + 1) from e
                table[(r, c)] = out
                inp = out
                if trace is not None:
                    trace.append(f"r{r + 1}c{c + 1}  {st.text:<24} -> {short(out)}")
                if st.kind == "emit":
                    emitted.append(out)
                    pos.append((r + 1, c + 1))
        results = []
        for slot, v, (pr, pc) in zip(self.slots, emitted, pos):
            try:
                results.append(self._convert(slot, v))
            except LangError as e:
                e.row, e.col = pr, pc
                raise
        return results[0] if len(results) == 1 else tuple(results)

    def _convert(self, slot, v):
        if isinstance(v, Grouped):
            raise RunError("emitting un-aggregated groups; add an aggregate after the #")
        if v is None:
            if not slot.nullable:
                raise RunError(f"output {slot.label} came out as none, but the signature does not allow it; "
                               f"write {slot.label}|none if that is intended")
            return None
        if slot.fields:
            n = len(slot.fields)

            def tup(it):
                if isinstance(it, dict):
                    if len(it) != n:
                        hint = " Pick the ones you want with *(..)." if len(it) > n else ""
                        raise RunError(f"output {slot.label} expects {n} fields but items have {len(it)}: "
                                       f"{', '.join(map(str, it))}.{hint}")
                    return tuple(it.values())
                if isinstance(it, (tuple, list)) and len(it) == n:
                    return tuple(it)
                raise RunError(f"output {slot.label} expects pairs/records of {n} fields, got {short(it)}")
            return [tup(i) for i in v] if isinstance(v, list) else tup(v)
        return plain(v)

    def _exec(self, st, inp, args, table, r, c):
        k = st.kind
        if k == "empty":
            return inp
        if k == "tie":
            vals = [table[(r - o[1], c)] if o[0] == "tie" else ev(o, args) for o in st.operands]
            return eval_expr(vals, st.ops)
        if k == "source":
            data = args[st.name]
            if st.join is None:
                return data
            if inp is None:
                return None
            left = need_list(inp, f"join {st.text}")
            if not isinstance(data, list):
                raise RunError(f"input '{st.name}' must be a list to join")
            theirs, mine = st.join
            index = {}
            for rec in data:
                index.setdefault(get_field(rec, theirs), []).append(rec)
            out = []
            for l in left:
                for rec in index.get(get_field(l, mine), []):
                    m = dict(l)
                    for key, v in rec.items():
                        m.setdefault(key, v)      # left side wins on name clashes
                    out.append(m)
            return out
        if inp is None:                            # none flows through every other stage
            return None
        if k == "group":
            groups = {}
            for it in need_list(inp, st.text):
                groups.setdefault(key_of(it, st.f), []).append(it)
            return Grouped(st.f or "key", list(groups.items()))
        if k == "unique":
            seen, out = set(), []
            for it in need_list(inp, st.text):
                kk = key_of(it, st.f)
                if kk not in seen:
                    seen.add(kk)
                    out.append(it)
            return out
        if k == "filter":
            rhs, cmp_ = ev(st.rhs, args), CMP[st.op]
            return [it for it in need_list(inp, st.text) if cmp_(val(it, st.f), rhs)]
        if k == "ladder":
            cmp_ = CMP[st.op]

            def one(it):
                v = val(it, st.f)
                for thr, label in st.rungs:
                    if cmp_(v, ev(thr, args)):
                        return label
                return st.default
            if isinstance(inp, Grouped):
                need_list(inp, st.text)
            return [one(i) for i in inp] if isinstance(inp, list) else one(inp)
        if k == "pick":
            if isinstance(inp, Grouped):
                need_list(inp, st.text)
            return apply_pick(inp, st.fs)
        if k == "case":
            fn = str.lower if st.mode == "l" else str.upper
            if isinstance(inp, str):
                return fn(inp)
            if isinstance(inp, list) and all(isinstance(x, str) for x in inp):
                return [fn(x) for x in inp]
            raise RunError(f"{st.text} needs text, got {short(inp)}")
        if k == "words":
            if isinstance(inp, str):
                return inp.split()
            if isinstance(inp, list) and all(isinstance(x, str) for x in inp):
                return [w for x in inp for w in x.split()]
            raise RunError(f";w needs text, got {short(inp)}")
        if k == "agg":
            return aggregate(st.op, st.f, st.name, inp)
        if k == "sort":
            return sorted(need_list(inp, st.text), key=lambda it: val(it, st.f), reverse=st.desc)
        if k == "emit":
            v = inp
            if isinstance(v, Grouped):
                need_list(v, "^")
            if st.n is not None:
                lst = need_list(v, st.text)
                if st.one:
                    v = lst[0] if lst else None
                else:
                    n = ev(st.n, args)
                    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
                        raise RunError(f"{st.text}: count must be a non-negative integer, got {n!r}")
                    v = lst[:n]
            if st.fs:
                v = apply_pick(v, st.fs)
            return v
        raise AssertionError(k)


def compile_source(src):
    sig = None
    rows = []
    for ln, raw in enumerate(src.splitlines(), 1):
        s = raw.strip()
        if not s or s.startswith("--"):
            continue
        try:
            if sig is None:
                if not s.startswith("$"):
                    raise GrammarError("the first line must be the signature, like $[inputs]{outputs}")
                sig = (s,) + parse_sig(s)
                continue
            cells = split_cells(s)
            row = []
            for ci, t in enumerate(cells, 1):
                try:
                    row.append(parse_stage(t, sig[2]))
                except GrammarError as e:
                    e.row, e.col = len(rows) + 1, ci
                    raise
            rows.append(row)
        except GrammarError as e:
            if e.row is None:
                e.msg = f"line {ln}: {e.msg}"
            raise
    if sig is None:
        raise GrammarError("empty program: needs a signature line")
    return Program(sig[1], sig[2], sig[3], rows, sig[0])


def load(path):
    with open(path, encoding="utf-8") as f:
        return compile_source(f.read())
