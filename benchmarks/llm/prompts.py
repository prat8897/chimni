"""Build the system prompt for each condition and the user message for each task.

Every condition gets the same contract (prompts/contract.md), its own short "how solutions are run" section, and
few-shot pairs built from the repository's ten examples (prompts/fewshot/). Chimni also gets docs/SPEC.md and
docs/TUTORIAL.md, because a model cannot know the language otherwise; that documentation is part of Chimni's cost
and is reported as such.
"""
import json
from functools import lru_cache

from .common import PROMPTS_DIR, ROOT

FENCE_LANG = {"chimni": "chimni", "python": "python", "pandas": "python", "sql": "sql"}
LANGUAGE = {"chimni": "Chimni", "python": "Python", "pandas": "Python with pandas", "sql": "SQLite SQL"}
NONE_WORD = {"chimni": "the program emits none (declare the output slot with `|none`)",
             "python": "return None", "pandas": "return None",
             "sql": "your result has no rows, or the value is NULL"}
SOLUTION_FILE = {"chimni": "solution.chimni", "python": "solution.py", "pandas": "solution_pandas.py",
                 "sql": "solution.sql"}
SQL_RESULT = {"scalar": "the answer is the first column of the first row (no rows, or NULL, means none).",
              "column": "the answer is the list of first-column values of all rows, in row order.",
              "rows": "the answer is the list of all rows, in row order; each row's columns form one pair."}


def interface(condition, inputs, sql_meta=None):
    """The condition-specific line under each specification (also used for the few-shots)."""
    if condition in ("python", "pandas"):
        return f"Signature: `def solve({', '.join(inputs)}):`"
    if condition == "chimni":
        return f"Program inputs, in this order: `[{','.join(inputs)}]`"
    tables = sql_meta["tables"]
    tdesc = ", ".join(f"{t}({c})" if isinstance(c, str) else f"{t}({', '.join(c)})" for t, c in tables.items())
    params = [i for i in inputs if i not in tables]
    lines = [f"Tables: {tdesc or 'none'}",
             f"Parameters: {', '.join(':' + p for p in params) or 'none'}",
             f"SQL result: {SQL_RESULT[sql_meta['output']]}"]
    return "\n".join(lines)


def fewshots(condition):
    out = []
    for d in sorted((PROMPTS_DIR / "fewshot").iterdir()):
        sol = d / SOLUTION_FILE[condition]
        if not sol.exists():
            continue
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        spec = (d / "spec.md").read_text(encoding="utf-8").strip()
        out.append((spec, interface(condition, meta["inputs"], meta.get("sql")),
                    sol.read_text(encoding="utf-8").strip()))
    return out


@lru_cache(maxsize=None)
def system_prompt(condition):
    contract = (PROMPTS_DIR / "contract.md").read_text(encoding="utf-8").format(
        language=LANGUAGE[condition], none_word=NONE_WORD[condition])
    parts = [contract.strip(), (PROMPTS_DIR / f"{condition}.md").read_text(encoding="utf-8").strip()]
    if condition == "chimni":
        parts.append("# Chimni language reference\n\n" + (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8").strip())
        parts.append("# Chimni tutorial\n\n" + (ROOT / "docs" / "TUTORIAL.md").read_text(encoding="utf-8").strip())
    lang = FENCE_LANG[condition]
    shots = ["# Worked examples"]
    for spec, iface, sol in fewshots(condition):
        shots.append(f"## Task\n\n{spec}\n\n{iface}\n\n## Solution\n\n```{lang}\n{sol}\n```")
    parts.append("\n\n".join(shots))
    return "\n\n".join(parts) + "\n"


def user_prompt(task, condition):
    return f"## Task\n\n{task.spec.strip()}\n\n{interface(condition, task.inputs, task.meta.get('sql'))}\n"
