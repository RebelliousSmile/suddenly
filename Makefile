.PHONY: check lint typecheck test
.PHONY: docker-up docker-down docker-test docker-check docker-shell docker-migrate docker-build

# ─── Local ────────────────────────────────────────────────────────

check: lint typecheck test

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy suddenly/

test:
	pytest --cov=suddenly --cov-fail-under=80 --tb=short

# ─── Docker ───────────────────────────────────────────────────────

COMPOSE_DEV = docker compose -f docker-compose.dev.yml

docker-build:
	$(COMPOSE_DEV) build

docker-up:
	$(COMPOSE_DEV) up -d

docker-down:
	$(COMPOSE_DEV) down

docker-migrate:
	$(COMPOSE_DEV) exec web python manage.py migrate

docker-test:
	$(COMPOSE_DEV) exec web pytest --cov=suddenly --cov-fail-under=80 --tb=short

docker-check:
	$(COMPOSE_DEV) exec web make check

docker-shell:
	$(COMPOSE_DEV) exec web python manage.py shell
