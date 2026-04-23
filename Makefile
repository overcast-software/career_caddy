-include .env
-include .env.local
export

.PHONY: up up-core up-full down logs build shell-api shell-db migrate test-api test-frontend bootstrap ci ci-ai pipeline-url doctor doctor-poller list help

# ── Dev stack ──────────────────────────────────────────────────────────────

up: ## Start core dev stack (db + api + frontend + chat)
	docker compose down --remove-orphans 2>/dev/null || true
	docker compose up db api frontend chat

up-full: ## Start all services including browser-mcp
	docker compose down --remove-orphans 2>/dev/null || true
	USE_MCP_BROWSER_AGENT=True docker compose up

down: ## Stop all services and remove orphan containers
	docker compose down --remove-orphans

logs: ## Follow logs for all running services
	docker compose logs -f

build: ## Rebuild all images (use after dependency changes)
	docker compose build --no-cache

# ── Shells ─────────────────────────────────────────────────────────────────

shell-api: ## Open a bash shell in the running api container
	docker compose exec api bash

shell-db: ## Open a psql shell in the running db container
	docker compose exec db psql -U $${DB_USER:-postgres} $${DB_NAME:-job_hunting}

# ── Database ───────────────────────────────────────────────────────────────

migrate: ## Run Django migrations
	docker compose exec api python manage.py migrate

demo-data: ## Seed guest user (Danny Noonan) and demo data — run after migrate
	docker compose exec api python manage.py seed_guest

# ── Tests ──────────────────────────────────────────────────────────────────

test-api: ## Run Django test suite (requires running db service)
	docker compose exec api python manage.py test -v 2

test-frontend: ## Run Ember QUnit tests
	docker compose exec frontend npm run test:ember

# ── CI (Dagger) ────────────────────────────────────────────────────────────
# Requires Dagger CLI: curl -fsSL https://dl.dagger.io/dagger/install.sh | sh

ci: ## Run API + frontend CI checks locally via Dagger (lint, tests, no secrets needed)
	dagger -m ./dagger call build-api
	dagger -m ./dagger call build-frontend

ci-ai: ## Build the slim AI Docker image via Dagger (no camoufox — production image)
	dagger -m ./dagger call build-ai

# ── AI Pipeline ────────────────────────────────────────────────────────────
# Requires: CC_API_TOKEN and OPENAI_API_KEY set in .env or environment

pipeline-url: ## Scrape a single job URL  (usage: make pipeline-url URL=https://...)
	cd ai && uv run caddy-pipeline --url $(URL)

poller: ## Poll for hold scrapes against prod (pass ARGS="--engine chrome --headless")
	cd ai && uv run caddy-poller $(ARGS)

poller-local: ## Poll for hold scrapes against local dev (localhost:8000; set CC_API_TOKEN_LOCAL to override prod token)
	cd ai && CC_API_BASE_URL=http://localhost:8000 CC_API_TOKEN=$${CC_API_TOKEN_LOCAL:-$$CC_API_TOKEN} uv run caddy-poller $(ARGS)

# ── Bootstrap ──────────────────────────────────────────────────────────────

doctor: ## Check local environment is set up correctly
	@bash scripts/doctor.sh

doctor-poller: ## Check hold-poller environment
	@bash scripts/doctor.sh --poller

bootstrap: ## Check if app needs initialization (prints status)
	@curl -s http://localhost:8000/api/v1/initialize/ | python3 -m json.tool

list: ## List running Docker services
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
