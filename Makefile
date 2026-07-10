.PHONY: help bootstrap up down logs prod-up prod-down migrate seed test-api lint-api test-web build-web

help:
	@echo "Enterprise AI Workspace"
	@echo "  make bootstrap   - ensure .env exists"
	@echo "  make up          - start local docker compose"
	@echo "  make down        - stop local stack"
	@echo "  make prod-up     - start production compose"
	@echo "  make prod-down   - stop production compose"
	@echo "  make migrate     - alembic upgrade head"
	@echo "  make seed        - seed demo owner"
	@echo "  make test-api    - pytest + ruff"
	@echo "  make test-web    - tsc"
	@echo "  make build-web   - next build"

bootstrap:
	@test -f .env || cp .env.example .env
	@echo ".env ready"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

prod-up:
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

migrate:
	cd apps/api && PYTHONPATH=src alembic upgrade head

seed:
	cd apps/api && PYTHONPATH=src python -m scripts.seed

test-api:
	cd apps/api && PYTHONPATH=src python -m pytest tests -q
	cd apps/api && ruff check src tests || true

lint-api:
	cd apps/api && ruff check src tests

test-web:
	cd apps/web && npx tsc --noEmit

build-web:
	cd apps/web && npm run build
