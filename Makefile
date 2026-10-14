PYTHON ?= python
MAX_COST ?= 20

.PHONY: test bench-test bench-dry bench-freeze bench-run

test:
	$(PYTHON) -m unittest discover -s tests

bench-test:
	$(PYTHON) -m unittest discover -s benchmarks/llm/tests -t .

bench-dry:
	$(PYTHON) -m benchmarks.llm.run --dry-run
	$(PYTHON) -m benchmarks.llm.report --dry-run

bench-freeze:
	$(PYTHON) -m benchmarks.llm.run --freeze

bench-run:
	$(PYTHON) -m benchmarks.llm.run --max-cost $(MAX_COST)
	$(PYTHON) -m benchmarks.llm.report
