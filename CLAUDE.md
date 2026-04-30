# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

Three independently deployable submodules, each with its own `CLAUDE.md`:

- `frontend/` — Ember.js 6.x SPA (see `frontend/CLAUDE.md`)
- `api/` — Django REST Framework backend (see `api/CLAUDE.md` — not yet created)
- `agents/` — Pydantic-AI agents + MCP servers + browser scraper + hold-poller (see `agents/CLAUDE.md`)

Inside the `agents/` submodule, top-level peer folders advertise the heterogeneity:

- `agents/agents/` — Pydantic-AI agent definitions (the spine: job_extractor, obstacle, onboarding, career_caddy CRUD)
- `agents/mcp_servers/` — Four MCP servers; `chat_server.py` and `public_server.py` ship to prod (`:8031` chat, `:8030` public at `mcp.careercaddy.online`); `browser_server.py` and `career_caddy_server.py` are local-only
- `agents/browser/` — Camoufox + Playwright engine, credentials, sessions (local-only)
- `agents/scrape_graph/` — pydantic-graph state machine for scrape + extract
- `agents/pollers/` — long-running daemons (`hold_poller.py`, `score_poller.py`)
- `agents/tools/` — one-shot operator scripts (`manual_login`, `discover_sites`, `export_graph_structure`, `fetch_chromium`)
- `agents/lib/` — shared utilities (`api_tools.py` HTTP client, `toolsets.py`, `models/`, `history.py`, etc.)

### Sibling consumer (not a submodule)

`~/Network/syncthing/Projects/career_caddy_automation/` ("cc_auto") is a sibling toolkit for email triage and other workflows that drives Career Caddy entirely over HTTP — no Python imports cross the boundary. Self-hosters set the `CC_API_BASE_URL` / `CC_MCP_URL` / `CC_API_TOKEN` env trio and point cc_auto at their own Career Caddy domain.

## Getting Started (Full Local Dev)

```bash
# 1. Copy and configure the root environment file
cp .env.example .env
# Minimum required: set OPENAI_API_KEY (or ANTHROPIC_API_KEY)
# Leave DB_PASSWORD=postgres for local dev
# Leave SECRET_KEY blank — compose uses a dev fallback automatically

# 2. Start the core stack (DB + API + Frontend)
docker compose up --build

# Once all services are healthy (watch the logs), open:
# http://localhost:4200  →  the setup wizard appears on first run
```

**First-run setup wizard** — on a fresh database the frontend routes to `/setup`. Fill in username, email, and password. This hits `POST /api/v1/initialize/` and creates the first admin user. After that, `/setup` is permanently disabled and you'll be redirected to `/login`.

**With browser MCP server** (for Claude Desktop / MCP clients):

```bash
# Ensure agents/secrets.yml exists (job site credentials for browser automation)
cp agents/secrets.yml.example agents/secrets.yml

make up-ai
# Browser MCP:  http://localhost:3004/sse
```

**Chat-created scrapes default to `hold` status.** The chat server creates scrapes with `status="hold"` so the hold-poller picks them up. Without a running poller (`make poller` or `make poller-local`), these scrapes sit in `hold` forever. On fresh clones, start the poller or manually change scrape status to trigger processing.

**Running the AI pipeline directly** (no docker service needed):

```bash
# Scrape a single job URL
make scrape-url URL=https://example.com/job
```

## Makefile Shortcuts

```bash
make up               # core stack (db + api + frontend + chat)
make up-full          # + browser MCP server (port 3004); sets USE_MCP_BROWSER_AGENT=True
make down             # stop all services (removes orphans)
make build            # rebuild all images (use after dependency changes)
make logs             # follow all logs
make list             # tabular view of running services + ports
make shell-api        # bash shell in running api container
make shell-db         # psql shell in running db container
make migrate          # run Django migrations
make demo-data        # seed guest user (Danny Noonan) + demo data (run after migrate)
make test-api         # run API test suite
make test-frontend    # run Ember QUnit tests
make ci               # Dagger: lint + test API and frontend locally
make ci-ai            # Dagger: build slim AI image (no camoufox)
make scrape-url URL=https://...   # scrape one job URL → add to Career Caddy
make poller                          # hold-poller against prod (Camoufox default)
make poller ARGS="--engine chrome"   # hold-poller with Chromium + stealth (ARM/Pi)
make poller ARGS="--attended"        # headed browser with per-domain tabs; solve captchas manually (add --attended-delay for a 5s pre-preseed pause, or --attended-delay N for a custom wait)
make poller-local                    # hold-poller against localhost:8000 (uses CC_API_TOKEN_LOCAL)
make doctor                          # check local environment is set up correctly
make doctor-poller                   # check hold-poller environment
make bootstrap                       # print API initialization status (curl /initialize/)
```

## Port Map

| Service | Local dev | Docker dev | Production |
|---------|-----------|------------|------------|
| PostgreSQL | 5432 | 5432 | 5432 |
| Django API | 8000 | 8000 | 8025 |
| Ember frontend | 4200 | 4200 | 8087 |
| Browser MCP server | 3004 | 3004 | — |

AI services are local-only — they require browser automation (Camoufox). Email workflows have been moved to `career_caddy_automation`.

## System Architecture

```
frontend (Ember SPA :4200)
    ↕ JSON:API  Authorization: Bearer <jwt>
api (Django + SQLAlchemy + PostgreSQL :8000)
    ↑ REST API calls (CC_API_TOKEN API key)
agents (Pydantic-AI agents + MCP servers)
```

The **frontend** is a JSON:API client. The `application` adapter injects JWT auth headers and handles 401 → token refresh → retry automatically.

The **API** uses Django ORM for all models. Startup requires only `manage.py migrate`.

The **AI layer** runs locally. Agents chain MCP servers as tool providers. Email→JobPost orchestration now lives in the sibling repo `~/Projects/career_caddy_automation`, which consumes tools from `mcp.careercaddy.online/mcp`; this repo's `agents/` only ships the local browser/scrape agents and the hold-poller. The AI layer authenticates to the API using a long-lived API key (`CC_API_TOKEN`), not a JWT.

## Cross-Component Contracts

**API format**: All endpoints use JSON:API (`application/vnd.api+json`). Router accepts both `/endpoint` and `/endpoint/`.

**Authentication**:
- Frontend → API: JWT (`Authorization: Bearer <token>`, 60-min lifetime, auto-refresh)
- AI agents → API: API key (`Authorization: Api-Key <key>`, managed via `/api/v1/api-keys/`)

**Bootstrap detection**: Frontend GETs `/api/v1/healthcheck/` on every route. Response includes `bootstrap_open: true` when no users exist → routes to `/setup`. After initialization, `bootstrap_open` is always `false`.

**Public frontend routes** (no auth required — skip the guard in `frontend/app/routes/application.js`):
`setup`, `login`, `about` (redirects to `/docs`), `docs.*`

To add a new public route, expand the `isPublic` check in `frontend/app/routes/application.js:18`.

**Key non-CRUD endpoints**:
- `GET  /api/v1/healthcheck/` — health + bootstrap state
- `GET  /api/v1/initialize/` — check if initialization needed
- `POST /api/v1/initialize/` — create first user (only when DB is empty)
- `GET  /api/v1/career-data/` — full data export
- `POST /api/v1/generate-prompt/` — AI prompt generation

## Docker Deployment (Production)

```bash
# On the VPS, in the app directory:
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

`docker-compose.prod.yml` uses pre-built GHCR images and runs only the core stack (db + api + frontend).

## CI/CD with Dagger

Dagger pipelines live in `dagger/src/main.py`. They replace raw `docker build` in CI.

**Install Dagger CLI** (one-time):
```bash
curl -fsSL https://dl.dagger.io/dagger/install.sh | sh
```

**Run locally** (no secrets needed — Dagger uses its own Docker sidecar):
```bash
make ci           # lint + test API and frontend
make ci-ai        # build AI image (slow first run, downloads camoufox)
```

**Available Dagger functions:**
```bash
dagger -m ./dagger call build-api       # lint + test API (spins up postgres sidecar)
dagger -m ./dagger call build-frontend  # lint + test frontend
dagger -m ./dagger call build-ai        # build AI image with camoufox
dagger -m ./dagger call publish --registry-token=env:GITHUB_TOKEN --org=overcast-software --tag=latest
dagger -m ./dagger call deploy --ssh-key=file:~/.ssh/id_ed25519 --host=<vps> --app-dir=/opt/career-caddy --tag=latest
```

## Gitflow

```
feature/*  →  main
```

No `develop` branch in practice — feature branches are cut from `main` and PR'd back to `main`. Submodules (`api/`, `frontend/`, `agents/`) commit first; the parent repo bumps the submodule pointers after.

The `agents/` submodule is hosted at `github.com/overcast-software/career_caddy_agents` (over SSH); `api/` and `frontend/` are HTTPS. The GHCR image for the agents image keeps its historical name `ghcr.io/overcast-software/career_caddy_ai` so prod pulls don't break.

**Daily workflow:**
```bash
git checkout main && git pull
git checkout -b feature/my-thing        # or chore/... for housekeeping
# ... work inside submodules, then commit submodule first ...
git push -u origin feature/my-thing
# Open PR: feature/my-thing → main
```

Merging to `main` triggers the `Deploy` workflow (publish images → deploy to VPS).
