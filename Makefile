# ── Env loading ────────────────────────────────────────────────────────────
# WARNING — this is not a dotenv loader, it is a make `-include` directive.
# Make reads `.env` and `.env.local` AS MAKEFILES: every `KEY=VALUE` line
# becomes a make variable. `export` (next line) then propagates every
# make variable into each recipe's shell, SHADOWING whatever that variable
# held in the parent interactive shell (direnv, manual export, ~/.envrc…).
#
# Processing is top-to-bottom, last-write-wins:
#   `.env`       — sets CC_API_TOKEN=<prod>
#   `.env.local` — if it ALSO sets CC_API_TOKEN=<local>, that value
#                  overrides and every recipe (incl. `make poller`) will
#                  see the local token instead of your shell's prod value.
#
# If you maintain both files, keep the key names disjoint: put dev-only
# overrides under distinct names (`CC_API_TOKEN_LOCAL`, `DB_PASSWORD_LOCAL`,
# …) and reference them explicitly in the recipes that want dev values
# (see `poller-local:` below as a template). The shadow is silent —
# `echo $CC_API_TOKEN` in your terminal will still show the prod value;
# only `make`'s recipe sub-shell sees the override.
-include .env
-include .env.local
export

.PHONY: up up-core up-full down logs build shell-api shell-db migrate test-api test-frontend bootstrap ci ci-ai scrape-url doctor doctor-poller list help

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

lint-api: ## Ruff-lint api code (PATHS=... for a subset; defaults to whole tree)
	docker compose exec api ruff check $(if $(PATHS),$(PATHS),.)

lint-frontend: ## Prettier-check frontend (PATHS=... for files; defaults to whole tree)
	docker compose exec frontend npm run lint:format $(if $(PATHS),-- --check $(PATHS),)

format-frontend: ## Prettier auto-fix frontend (PATHS=... for files; defaults to whole tree)
	docker compose exec frontend npm run lint:format -- --write $(if $(PATHS),$(PATHS),.)

# ── CI (Dagger) ────────────────────────────────────────────────────────────
# Requires Dagger CLI: curl -fsSL https://dl.dagger.io/dagger/install.sh | sh
#
# Two-phase fail-fast layout: lint across both repos in parallel first
# (cheap; surfaces style/format/static breaks in ~30s), then tests in
# parallel (slow). A lint break in either repo aborts before tests run.
# Dagger's content-addressed cache reuses the apt/uv/npm setup steps
# between the lint and test functions, so the split is not duplicated work.

.PHONY: ci ci-lint ci-test
.PHONY: ci-lint-api ci-lint-frontend ci-test-api ci-test-frontend

ci-lint-api:
	dagger -m ./dagger call lint-api

ci-lint-frontend:
	dagger -m ./dagger call lint-frontend

ci-test-api:
	dagger -m ./dagger call test-api

ci-test-frontend:
	dagger -m ./dagger call test-frontend

ci-lint: ci-lint-api ci-lint-frontend
ci-test: ci-test-api ci-test-frontend

ci: ## Run API + frontend CI checks locally via Dagger (lint then tests, parallel within each phase)
	$(MAKE) -j2 ci-lint
	$(MAKE) -j2 ci-test

ci-ai: ## Build the slim AI Docker image via Dagger (no camoufox — production image)
	dagger -m ./dagger call build-ai

# ── AI Pipeline ────────────────────────────────────────────────────────────
# Requires: CC_API_TOKEN and OPENAI_API_KEY set in .env or environment

scrape-url: ## Scrape a single job URL  (usage: make scrape-url URL=https://...)
	cd agents && uv run caddy-pipeline --url $(URL)

poller: ## Poll for hold scrapes against prod (pass ARGS="--engine chrome --headless")
	cd agents && uv run caddy-poller $(ARGS)

poller-local: ## Poll for hold scrapes against local dev (localhost:8000; set CC_API_TOKEN_LOCAL to override prod token)
	cd agents && CC_API_BASE_URL=http://localhost:8000 CC_API_TOKEN=$${CC_API_TOKEN_LOCAL:-$$CC_API_TOKEN} uv run caddy-poller $(ARGS)

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
