.PHONY: help up down logs migrate seed backup restore test lint build deploy

# === Environment ===
ENV ?= dev
COMPOSE_FILE := infra/docker-compose.yml
ifeq ($(ENV),prod)
    COMPOSE_FILE := infra/docker-compose.prod.yml
endif

# === Help ===
help:
	@echo "FindableX Platform Commands"
	@echo ""
	@echo "Development:"
	@echo "  make up          - Start all services"
	@echo "  make up-crawler  - Start with crawler service"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View logs (follow mode)"
	@echo "  make logs-api    - View API logs only"
	@echo "  make shell-api   - Open shell in API container"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     - Run database migrations"
	@echo "  make migrate-new - Create new migration"
	@echo "  make seed        - Seed database with test data"
	@echo "  make backup      - Backup database"
	@echo "  make restore     - Restore database from backup"
	@echo ""
	@echo "Testing:"
	@echo "  make test        - Run all tests"
	@echo "  make test-api    - Run API tests only"
	@echo "  make lint        - Run linters"
	@echo ""
	@echo "Production:"
	@echo "  make build       - Build all images"
	@echo "  make deploy      - Deploy to production"

# === Development ===
up:
	docker compose -f $(COMPOSE_FILE) up -d

up-crawler:
	docker compose -f $(COMPOSE_FILE) --profile crawler up -d

up-monitoring:
	docker compose -f $(COMPOSE_FILE) --profile monitoring up -d

down:
	docker compose -f $(COMPOSE_FILE) down

restart:
	docker compose -f $(COMPOSE_FILE) restart

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

logs-api:
	docker compose -f $(COMPOSE_FILE) logs -f api

logs-worker:
	docker compose -f $(COMPOSE_FILE) logs -f worker

shell-api:
	docker compose -f $(COMPOSE_FILE) exec api bash

shell-db:
	docker compose -f $(COMPOSE_FILE) exec postgres psql -U findablex

# === Database ===
migrate:
	docker compose -f $(COMPOSE_FILE) exec api alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	docker compose -f $(COMPOSE_FILE) exec api alembic revision --autogenerate -m "$$msg"

migrate-down:
	docker compose -f $(COMPOSE_FILE) exec api alembic downgrade -1

seed:
	docker compose -f $(COMPOSE_FILE) exec api python -m app.db.seed

backup:
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose -f $(COMPOSE_FILE) exec -T postgres \
		pg_dump -U findablex findablex | gzip > backups/backup_$$TIMESTAMP.sql.gz; \
	echo "Backup saved to backups/backup_$$TIMESTAMP.sql.gz"

restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore FILE=backups/backup_xxx.sql.gz"; \
		exit 1; \
	fi
	@gunzip -c $(FILE) | docker compose -f $(COMPOSE_FILE) exec -T postgres \
		psql -U findablex findablex
	@echo "Restore completed from $(FILE)"

# === Testing ===
test:
	docker compose -f $(COMPOSE_FILE) exec api pytest
	docker compose -f $(COMPOSE_FILE) exec web npm test

test-api:
	docker compose -f $(COMPOSE_FILE) exec api pytest -v

test-cov:
	docker compose -f $(COMPOSE_FILE) exec api pytest --cov=app --cov-report=html

lint:
	docker compose -f $(COMPOSE_FILE) exec api ruff check .
	docker compose -f $(COMPOSE_FILE) exec api mypy .
	docker compose -f $(COMPOSE_FILE) exec web npm run lint

# === Build & Deploy ===
build:
	docker build -t findablex-api:latest -f docker/api/Dockerfile packages/api
	docker build -t findablex-worker:latest -f docker/worker/Dockerfile packages/worker
	docker build -t findablex-crawler:latest -f docker/crawler/Dockerfile packages/crawler
	docker build -t findablex-web:latest -f docker/web/Dockerfile packages/web

push:
	docker push $(REGISTRY)/findablex-api:$(VERSION)
	docker push $(REGISTRY)/findablex-worker:$(VERSION)
	docker push $(REGISTRY)/findablex-crawler:$(VERSION)
	docker push $(REGISTRY)/findablex-web:$(VERSION)

deploy:
	@echo "Deploying version $(VERSION) to production..."
	ssh $(DEPLOY_HOST) "cd /opt/findablex && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"

# === Maintenance ===
clean:
	docker compose -f $(COMPOSE_FILE) down -v --remove-orphans
	docker system prune -f

clean-all:
	docker compose -f $(COMPOSE_FILE) down -v --remove-orphans
	docker system prune -af --volumes

# === Local Development (without Docker) ===
dev-api:
	cd packages/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	cd packages/worker && celery -A app.celery_app worker --loglevel=info

dev-web:
	cd packages/web && npm run dev
