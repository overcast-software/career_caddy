# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

Three independently deployable components, each with its own `CLAUDE.md`:

- `frontend/` — Ember.js 6.x SPA (see `frontend/CLAUDE.md`)
- `api/` — Django REST Framework backend (see `api/CLAUDE.md` — not yet created)
- `ai/` — Pydantic-AI agents + MCP servers (see `ai/CLAUDE.md`)

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
# Ensure ai/secrets.yml exists (job site credentials for browser automation)
cp ai/secrets.yml.example ai/secrets.yml

make up-ai
# Browser MCP:  http://localhost:3004/sse
```

**Chat-created scrapes default to `hold` status.** The chat server creates scrapes with `status="hold"` so the hold-poller picks them up. Without a running poller (`make poller` or `make poller-local`), these scrapes sit in `hold` forever. On fresh clones, start the poller or manually change scrape status to trigger processing.

**Running the AI pipeline directly** (no docker service needed):

```bash
# Scrape a single job URL
make pipeline-url URL=https://example.com/job
```

## Makefile Shortcuts

```bash
make up               # core stack (db + api + frontend)
make up-ai            # + browser MCP server (port 3004)
make down             # stop all services
make logs             # follow all logs
make shell-api        # bash shell in running api container
make shell-db         # psql shell in running db container
make migrate          # run Django migrations
make test-api         # run API test suite
make test-frontend    # run Ember QUnit tests
make ci               # Dagger: lint + test API and frontend locally
make pipeline-url URL=https://...   # scrape one job URL → add to Career Caddy
make poller                          # hold-poller against prod (Camoufox default)
make poller ARGS="--engine chrome"   # hold-poller with Chromium + stealth (ARM/Pi)
make poller-local                    # hold-poller against localhost:8000
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
ai (Pydantic-AI agents + MCP servers)
```

The **frontend** is a JSON:API client. The `application` adapter injects JWT auth headers and handles 401 → token refresh → retry automatically.

The **API** uses Django ORM for all models. Startup requires only `manage.py migrate`.

The **AI layer** runs locally. Agents chain MCP servers as tool providers. The pipeline (`job_email_to_caddy.py`) orchestrates: URL → browser scrape → Career Caddy API POST. The AI layer authenticates to the API using a long-lived API key (`CC_API_TOKEN`), not a JWT.

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
feature/*  →  develop  →  main
```

- **`feature/*`** — open PR to `develop`; triggers `CI` workflow (build-api + build-frontend)
- **`develop`** — integration branch; same CI checks on push
- **`main`** — production; merging here triggers `Deploy` workflow (publish images → deploy to VPS)

**Setup** (one-time):
```bash
git checkout main && git pull
git checkout -b develop
git push -u origin develop
# GitHub → Settings → Branches → set default branch to develop
# Add protection rules: main requires PR + CI; develop requires PR
```

**Daily workflow:**
```bash
git checkout develop && git pull
git checkout -b feature/my-thing
# ... work ...
git push -u origin feature/my-thing
# Open PR: feature/my-thing → develop
```
