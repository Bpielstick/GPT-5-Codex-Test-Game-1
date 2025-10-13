PY=python
PKG=ainovelwriter

.PHONY: install qa test lint type fmt run
install:
	pip install -e . && pip install -r requirements-dev.txt

qa: lint type test
lint:
	ruff check .
fmt:
	ruff format .
type:
	mypy $(PKG) examples
test:
	pytest -q
run:
	PYTHONPATH=. $(PY) examples/run_pipeline.py
