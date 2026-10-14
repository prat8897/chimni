"""Shared pieces: paths, tasks, input generation, and output comparison."""
import importlib.util
import json
import math
import random
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TASKS_DIR = HERE / "tasks"
PROMPTS_DIR = HERE / "prompts"
RESULTS_DIR = HERE / "results"
CHIMNI_SRC = ROOT / "src"

CONDITIONS = ["chimni", "python", "pandas", "sql"]
N_RANDOM = 300
REL_TOL = 1e-9
ABS_TOL = 1e-9


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@dataclass
class Task:
    id: str                       # "13_units_sold_by_product"
    dir: Path
    meta: dict
    spec: str
    edge_cases: list = field(repr=False)

    @property
    def difficulty(self):
        return self.meta["difficulty"]

    @property
    def expressible(self):
        return self.meta["expressible"]

    @property
    def inputs(self):
        return self.meta["inputs"]

    def has(self, condition):
        return condition in self.meta["conditions"]

    def reference_fn(self):
        return _reference(str(self.dir / "reference.py"), self.id)

    def reference_code(self, condition):
        """The trusted solution in a condition's language (used by tests and the mock model), or None."""
        name = {"python": "reference.py", "pandas": "reference_pandas.py", "sql": "reference.sql",
                "chimni": "reference.chimni"}[condition]
        p = self.dir / name
        return p.read_text(encoding="utf-8") if p.exists() else None

    def test_inputs(self):
        """[(kind, label, input)] - the hand-written edge cases first, then N_RANDOM seeded random inputs."""
        out = [("edge", e["name"], e["input"]) for e in self.edge_cases]
        gen = _load_module(self.dir / "input_gen.py", "gen_" + self.id).generate
        rng = random.Random("chimni-llm-bench:" + self.id)
        out += [("random", f"random #{i}", gen(rng)) for i in range(N_RANDOM)]
        return out


@lru_cache(maxsize=None)
def _reference(path, task_id):
    return _load_module(Path(path), "ref_" + task_id).solve


def load_tasks(only=None):
    tasks = []
    for d in sorted(p for p in TASKS_DIR.iterdir() if p.is_dir()):
        if only and not any(d.name == o or d.name.split("_", 1)[0] == o or d.name.endswith(o) for o in only):
            continue
        tasks.append(Task(
            id=d.name, dir=d,
            meta=json.loads((d / "meta.json").read_text(encoding="utf-8")),
            spec=(d / "spec.md").read_text(encoding="utf-8"),
            edge_cases=json.loads((d / "edge_cases.json").read_text(encoding="utf-8")),
        ))
    return tasks


def load_invalid():
    p = HERE / "INVALID.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    return {row["task"]: row["reason"] for row in data}


# ------------------------------------------------------------- comparison
def to_plain(v):
    """Tuples -> lists, numpy scalars -> Python numbers; anything else unchanged."""
    if isinstance(v, (list, tuple)):
        return [to_plain(x) for x in v]
    if isinstance(v, dict):
        return {k: to_plain(x) for k, x in v.items()}
    if hasattr(v, "item") and type(v).__module__.startswith("numpy"):
        return v.item()
    return v


def same(a, b):
    """Structural equality after to_plain(); numbers compare with a tiny tolerance, bools never equal numbers."""
    a, b = to_plain(a), to_plain(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, float) and math.isnan(a) or isinstance(b, float) and math.isnan(b):
            return False
        return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    return type(a) is type(b) and a == b


def short(v, n=300):
    s = json.dumps(to_plain(v), default=repr)
    return s if len(s) <= n else s[: n - 1] + "…"
