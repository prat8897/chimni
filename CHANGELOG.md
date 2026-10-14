# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/) once it reaches 1.0 (until then, minor versions may change the language).

## [Unreleased]

### Added
- **jq-style command line.** Pipe JSON, JSON Lines or CSV in; write the program inline (the signature is inferred);
  get JSON or CSV out (`-o csv`, `-c`). Inputs bind from stdin, files (by file name or `name=file`), JSON literals
  and `--arg name=value`. `--trace` now prints to stderr.
- **`chimni fmt`** lines cells up into columns (`-w` to rewrite, `--check` for CI). Only whitespace changes.
- **VS Code syntax highlighting** in `editors/vscode/`.
- **A website with an in-browser playground** (Pyodide): live re-runs, an **animated dataflow view** in which cells
  fire left to right, independent rows fire together and tie arrows draw as they're read, shareable links, and a
  "Limits & tricks" section. Source in `site/`, deployed by `.github/workflows/pages.yml`.
- **The fair comparison:** every example has an idiomatic pandas, SQL or jq version in `examples/compare/`, tested
  against Chimni on random inputs in CI; sample inputs in `examples/inputs/`.

### Changed
- **Ties between two streams of aggregate records pair them by key**, not by position, so two grouped rows line up
  even when their groups come out in a different order. Different keys are a run error. Previously this gave a
  silently wrong answer.
- The CLI prints JSON by default (`-o repr` for the old Python-style output). A `.chimni` file with no data is still
  only checked; use `--check` to be explicit.
- `benchmarks/size.py` reports the pandas/SQL/jq column and counts every column's characters with whitespace squeezed
  (previously only Chimni's were squeezed, which flattered it). Token counts were removed.

## [0.1.0] - 2026-10-13

First public release.

### Added
- Interpreter for the Chimni 2D dataflow language: signature, rows of cells, ties, and the cell set documented in
  [docs/SPEC.md](docs/SPEC.md).
- Grid checks before running (empty-left cells, bad ties, wrong number of outputs, unknown names) and run-time checks
  with row/column positions (missing fields, un-aggregated groups, output shape, `|none`).
- Command line (`chimni file.chimni '{...}' --trace --json`) and Python API (`chimni.load`, `chimni.compile_source`).
- Ten examples, each beside its Python original, tested against it on random inputs; the SQL example is also checked
  against real SQL run by `sqlite3`.
- `benchmarks/size.py`: code size comparison.
