# Contributing to Chimni

Thank you for being here. Chimni is v0.1 and the design is still soft, so every kind of contribution matters:
code, examples, benchmarks, and — especially — arguments about the grammar.

## Setup

```bash
git clone https://github.com/prat8897/chimni.git && cd chimni
pip install -e .                              # no runtime dependencies
python -m unittest discover -s tests -v       # should finish in well under a second
chimni examples/10_grade.chimni '{"score": 91}'
```

Python 3.9+. The interpreter deliberately uses only the standard library.

## Good first contributions

- **Write a new example.** Take a short Python or SQL script, port it to Chimni, and add `examples/NN_name.chimni`,
  `examples/python/NN_name.py`, the idiomatic pandas/SQL/jq version in `examples/compare/`, a sample input in
  `examples/inputs/NN_name.json`, and a generator in `tests/test_examples.py`. If the port was awkward, that's the most
  valuable part — open an issue describing what was missing.
- **Make an error message better.** Try to break a program on purpose; if the message didn't point at the problem,
  fix it and add a test in `tests/test_errors.py`.
- **Editor support:** a Tree-sitter grammar, publishing the VS Code extension in `editors/vscode/`, or a grammar for
  another editor.
- **A SQL / DuckDB backend:** compile a row to a query, so programs run on data that doesn't fit in memory.
- **More CLI input formats:** Parquet, TSV with headers, NDJSON from APIs.
- **Playground features:** the site lives in `site/` (`python site/build.py`, then serve `_site/`).

## Adding a cell (a new symbol)

Chimni's vocabulary is closed on purpose, so new cells need a reason. A good proposal says what Python/SQL it replaces
and shows **three** real programs that need it. Then:

1. `parse_stage` in `src/chimni/interpreter.py` — parse it into a `Stage`.
2. `Program._exec` — implement it. Cells must not mutate their input, and `None` must flow through (the dispatcher
   already handles that for you).
3. `Program._check` — if it affects "has input on its left" analysis, update it.
4. `docs/SPEC.md` — add it to the cell table, and note any decisions.
5. A test, and ideally an example, that uses it.

## Language-design changes

Open an issue using the **Language design** template *before* writing code. Please include a before/after in Chimni,
the Python it replaces, and what it breaks. See [docs/DESIGN.md](docs/DESIGN.md) for the open questions — good
proposals often start there.

## Pull requests

- Keep them small and focused; one idea each.
- Run `python -m unittest discover -s tests` before pushing. Every example is checked against its Python original on
  random inputs, so a passing suite means the languages still agree.
- If you change behaviour, update `docs/SPEC.md` and `CHANGELOG.md` in the same PR.

## Conduct

Be kind, assume good faith, and keep critique about the work. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
