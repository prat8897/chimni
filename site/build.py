#!/usr/bin/env python3
"""Build the GitHub Pages site into _site/.

    python site/build.py
    python -m http.server -d _site 8000      # then open http://localhost:8000

The page runs the real interpreter (src/chimni) in the browser with Pyodide. This script copies it
next to the page, and bundles every example with its sample input, its Python original, its
pandas / SQL / jq counterpart, size numbers, and a pre-rendered run (shown while Python loads).
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = ROOT / "_site"
EX = ROOT / "examples"

sys.path[:0] = [str(ROOT / "src"), str(SITE), str(ROOT / "benchmarks")]
import playground  # noqa: E402
import size  # noqa: E402


def pretty(args):
    """One input per line, one list item per line - short enough to read and edit."""
    def value(v):
        if isinstance(v, list) and v:
            return "[\n" + ",\n".join("    " + json.dumps(x) for x in v) + "\n  ]"
        return json.dumps(v)
    return "{\n" + ",\n".join(f"  {json.dumps(k)}: {value(v)}" for k, v in args.items()) + "\n}"


def examples():
    sizes = {d["example"]: d for d in size.measure(size.tokenizer())}
    out = []
    for c in sorted(EX.glob("*.chimni")):
        src = c.read_text(encoding="utf-8")
        inputs = (EX / "inputs" / (c.stem + ".json")).read_text(encoding="utf-8")
        alt = size.alternative_path(c.stem)
        first = src.splitlines()[0]
        out.append({
            "stem": c.stem,
            "title": first[2:].strip() if first.startswith("--") else c.stem,
            "program": src,
            "inputs": pretty(json.loads(inputs)),
            "python": (EX / "python" / (c.stem + ".py")).read_text(encoding="utf-8"),
            "alt": {"lang": size.LANG[alt.suffix], "file": f"examples/compare/{alt.name}",
                    "code": alt.read_text(encoding="utf-8")},
            "size": sizes[c.stem],
            "prerun": json.loads(playground.run(src, inputs)),
        })
    return out


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for name in ["index.html", "style.css", "app.js", "playground.py"]:
        shutil.copy(SITE / name, OUT / name)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / "py" / "chimni").mkdir(parents=True)
    for name in ["__init__.py", "interpreter.py"]:
        shutil.copy(ROOT / "src" / "chimni" / name, OUT / "py" / "chimni" / name)
    (OUT / "examples.json").write_text(json.dumps(examples()), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"built {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
