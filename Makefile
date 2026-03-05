.PHONY: check lint typecheck test

check: lint typecheck test

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy suddenly/

test:
	pytest --cov=suddenly --cov-fail-under=80 --tb=short
