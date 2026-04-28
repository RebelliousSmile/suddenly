.PHONY: check lint typecheck test i18n-check frontend
.PHONY: docker-up docker-down docker-test docker-check docker-shell docker-migrate docker-build docker-logs

# ─── Local ────────────────────────────────────────────────────────

check: lint typecheck test i18n-check

i18n-check:
	python manage.py makemessages -l fr -l en --no-wrap --ignore=venv --ignore=node_modules --ignore=staticfiles
	python manage.py compilemessages -l fr -l en
	pytest tests/core/test_i18n.py tests/core/test_locale_formatting.py -v

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy suddenly/

test:
	pytest --cov=suddenly --cov-fail-under=80 --tb=short

frontend:
	cd frontend && npm install && npm run build

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

docker-logs:
	$(COMPOSE_DEV) logs -f web

docker-createsuperuser:
	$(COMPOSE_DEV) exec web python manage.py createsuperuser
