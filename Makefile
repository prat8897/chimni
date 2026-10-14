PYTHON ?= python

.PHONY: test site serve

test:
	$(PYTHON) -m unittest discover -s tests

site:
	$(PYTHON) site/build.py

serve: site
	$(PYTHON) -m http.server -d _site 8000
