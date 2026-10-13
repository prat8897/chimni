# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/) once it reaches 1.0 (until then, minor versions may change the language).

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
- `benchmarks/size.py`: code size comparison, with token counts when `tiktoken` is available.
