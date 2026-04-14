.PHONY: up up-mcp-gateway down logs build shell-api shell-db migrate test-api test-frontend bootstrap ci ci-ai pipeline pipeline-url help

# ── Dev stack ──────────────────────────────────────────────────────────────

up: ## Start full dev stack (db + api + frontend + chat + browser-mcp)
	docker compose down --remove-orphans 2>/dev/null || true
	docker compose up

up-mcp-gateway: ## Start full stack + MCP gateway aggregator (port 3002)
	docker compose down --remove-orphans 2>/dev/null || true
	docker compose --profile mcp-gateway up

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
# For email mode: also requires NOTMUCH_MAILDIR set and notmuch indexed

pipeline: ## Run the full job email → Career Caddy pipeline
	cd ai && uv run caddy-pipeline

pipeline-url: ## Scrape a single job URL  (usage: make pipeline-url URL=https://...)
	cd ai && uv run caddy-pipeline --url $(URL)

poller: ## Poll for hold scrapes and process locally (headed browser)
	cd ai && uv run caddy-poller

# ── Bootstrap ──────────────────────────────────────────────────────────────

bootstrap: ## Check if app needs initialization (prints status)
	@curl -s http://localhost:8000/api/v1/initialize/ | python3 -m json.tool

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
