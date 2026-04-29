# Career Caddy

A personal job hunt dashboard. Track applications, store job postings, manage your resume, and generate AI-assisted cover letters and application answers.

## What Is This?

Career Caddy is an AI-assisted, self-hosted job search tracker. The core problem it solves:
job hunting is fragmented across dozens of websites with no central place for your activity,
applications, or documents.

The app is built around one philosophy: **Career Data is the center of everything.** Career
Data is a markdown document you write once and refine over time — your professional background,
skills, writing voice, and goals. Every AI feature (scoring, cover letters, summaries, answer
drafting, chat) uses Career Data as its foundational prompt context. Better Career Data means
better AI output across the board.

See the in-app documentation at `/docs` for the intended user workflow and explanation of
every resource.

## Architecture Overview

| Component | Stack | Role |
|-----------|-------|------|
| `frontend/` | Ember.js 6.x SPA | User interface, JSON:API client |
| `api/` | Django REST Framework | Data layer, extraction, AI orchestration |
| `agents/` | Pydantic-AI + MCP servers | Browser automation, email pipeline, agents |
| Chat service | Starlette SSE (in `agents/`) | Streaming AI chat with page-context awareness |
| MCP server | FastMCP (in `agents/`) | Public read-only career data tools for MCP clients |
| Hold-poller | Standalone worker (in `agents/`) | Polls API for queued scrapes, runs browser locally |

**Why Ember.js?** The app has complex nested routes (job post → application → question →
answer) and many inter-resource relationships. Ember's conventions for nested routing, the
Ember Data store, and the JSON:API adapter handle this complexity cleanly.

**Why Django?** Django handles authentication, migrations, and admin.
The 30+ domain models benefit from its ORM and ecosystem.

**Why a separate AI layer?** The pipeline needs browser automation (Camoufox) and local
email access (notmuch) — host-only capabilities that don't belong in a container. Running
them as MCP servers makes them composable with any MCP client (Claude Desktop, etc.).

## Key Features

- **Tiered extraction** — Domain profiles learn from past scrapes, auto-selecting from CSS-only ($0) to full LLM ($0.10). See `agents/CLAUDE.md` for model config.
- **Hold-poller** — Headless browser worker that runs on a desktop or Raspberry Pi, scraping jobs the VPS cannot handle. The VPS queues work; the poller executes it.
- **AI chat** — SSE streaming assistant aware of your current page context, with elicitation buttons for guided workflows.
- **MCP integration** — Public career data tools exposable to any MCP client (Claude Desktop, Cursor, etc.).
- **Screenshots** — Browser captures stored during scraping, viewable in a staff-only gallery for debugging.
- **Domain scrape profiles** — Per-hostname learning loop: auth requirements, CSS selectors, extraction hints. Staff-editable in admin.

## Deployment Topology

The system splits across two (optionally three) machines:

| Target | Compose file | Services | Recommended hardware |
|--------|-------------|----------|----------------------|
| **VPS** (production) | `docker-compose.prod.yml` | db, api, frontend, chat, mcp | 2 GB RAM, 1–2 vCPU, no GPU |
| **Local dev** | `docker-compose.yml` | db, api, frontend, chat, browser-mcp | 8+ GB RAM (Camoufox needs ~1 GB) |
| **Raspberry Pi / NUC** (optional) | standalone script | hold-poller only | Pi 4/5 with 4+ GB RAM, 64-bit OS |

**How hold-poller bridges the gap:** The VPS runs no browser. When a scrape is created with `status=hold`, the hold-poller (running locally or on a Pi) picks it up, scrapes the page with Camoufox, and posts the raw HTML back to the API. The API then handles extraction, job post creation, and scoring — no LLM runs on the poller.

## The Data Model at a Glance

- **Career Data** — singleton per user, markdown blob, read on every AI call
- **Job Post** — root resource; Scores, Cover Letters, Summaries, Scrapes, and Applications all link to it
- **Scrape** — raw HTML capture of a job page; **Job Post** is the structured extraction from a scrape
- **Score** — AI fit assessment (0–100); run before writing a cover letter to prioritize your time
- **Questions / Answers** — exist at both application level and globally (companies reuse questions; you can reuse answers)
- **Favorite flag** — on Cover Letters and Answers, feeds those outputs back into Career Data to improve future AI generations

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose v2
- [Make](https://www.gnu.org/software/make/) (`make --version` to check)
- An OpenAI or Anthropic API key (for AI features — cover letters, summaries, scoring, chat)
- [uv](https://docs.astral.sh/uv/) (only if running the hold-poller outside Docker)

## Quick Start

```bash
# 1. Copy the environment file and fill in your API key
cp .env.example .env
# Open .env and set OPENAI_API_KEY=sk-... (or ANTHROPIC_API_KEY)
# Everything else can stay as-is for local dev

# 2. Check your environment
make doctor

# 3. Start the app
make up

# 4. Open the app
# http://localhost:4200
```

The first time you open the app, a setup wizard will appear. Enter a username, email, and password — this creates your admin account. The wizard only runs once.

> The first `make up` takes a few minutes while Docker builds the images and installs dependencies. Subsequent starts are fast.

## Stopping

```bash
make down
```

## Ports

| Service | Local dev | Production |
|---------|-----------|------------|
| Frontend | :4200 | :8087 |
| API | :8000 | :8025 |
| Database | :5432 | :5432 |
| Chat | internal | :8031 |
| Browser MCP | :3004 | — |
| MCP gateway | :3002 | — |
| Public MCP | — | :8030 |

## Common Commands

```bash
make up              # Start the full dev stack
make up-full         # Dev stack + hold-poller (scrapes hold jobs locally)
make down            # Stop everything
make logs            # Follow live logs from all services
make doctor          # Check your environment is set up correctly
make doctor-poller   # Check hold-poller environment specifically
make poller          # Run the hold-poller standalone
make shell-api       # Open a shell inside the API container
make shell-db        # Open a psql shell in the database
make migrate         # Run database migrations manually
make demo-data       # Seed a guest user and demo data
make ci              # Run API + frontend CI checks locally via Dagger
make help            # List all available commands
```

## Hold-Poller Setup

The hold-poller is a standalone Python process that bridges the gap between the VPS (no browser) and sites that require JavaScript rendering.

```bash
# 1. Ensure these are set in .env:
#    CC_API_BASE_URL=https://careercaddy.online  (or http://localhost:8000)
#    CC_API_TOKEN=<your-api-key>                 (from /admin/api-keys)

# 2. Run it
make poller
# Or directly: cd agents && uv run caddy-poller
```

The poller polls the API every 30 seconds (configurable via `HOLD_POLL_INTERVAL`). It backs off exponentially when there's no work, and resets on success.

For Raspberry Pi deployment, see `~/Sandbox/caddy-browser-pi/`.

## Optional: Logfire Tracing

The browser MCP server supports [Logfire](https://logfire.pydantic.dev/) tracing. It is disabled by default and requires no setup to run without it.

**Getting a token:**

1. Sign up at [logfire.pydantic.dev](https://logfire.pydantic.dev/)
2. Create a project (e.g. `career-caddy`)
3. Go to **Settings → Write tokens** and create a new token
4. Copy the token value

Then set it in your `.env` file:

```
LOGFIRE_TOKEN=your-token-here
```

## Troubleshooting

**Port already in use** — `make up` stops existing containers before starting, but if another app on your machine uses port 4200, 8000, or 5432, you'll see an error. Stop the conflicting service and run `make up` again.

**Setup wizard doesn't appear** — the API may still be starting. Wait 30 seconds and refresh.

**Slow first load** — the frontend compiles Tailwind CSS on first start. Subsequent reloads are instant.

**Hold-poller can't reach the API** — run `make doctor-poller` to diagnose. Check that `CC_API_BASE_URL` and `CC_API_TOKEN` are set in `.env` and that the target API is running.

**Want to start fresh** — stop the app, remove the database volume, and restart:
```bash
make down
docker volume rm career_caddy_deploy_postgres_data
make up
```
