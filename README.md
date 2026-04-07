# Career Caddy

A personal job hunt dashboard. Track applications, store job postings, manage your resume, and generate AI-assisted cover letters and application answers.

## What Is This?

Career Caddy is an AI-assisted, self-hosted job search tracker. The core problem it solves:
job hunting is fragmented across dozens of websites with no central place for your activity,
applications, or documents.

The app is built around one philosophy: **Career Data is the center of everything.** Career
Data is a markdown document you write once and refine over time — your professional background,
skills, writing voice, and goals. Every AI feature (scoring, cover letters, summaries, answer
drafting) uses Career Data as its foundational prompt context. Better Career Data means better
AI output across the board.

See the in-app documentation at `/docs` for the intended user workflow and explanation of
every resource.

## Architecture Overview

Three independently deployable components:

| Component | Stack | Role |
|-----------|-------|------|
| `frontend/` | Ember.js 6.x SPA | User interface, JSON:API client |
| `api/` | Django REST Framework | Data layer, AI orchestration endpoints |
| `ai/` | Pydantic-AI + MCP servers | Browser automation, email pipeline, agents |

**Why Ember.js?** The app has complex nested routes (job post → application → question →
answer) and many inter-resource relationships. Ember's conventions for nested routing, the
Ember Data store, and the JSON:API adapter handle this complexity cleanly.

**Why Django + SQLAlchemy?** Django handles authentication, migrations, and admin.
SQLAlchemy handles the 30+ domain models, which benefit from its richer query expressiveness.

**Why a separate AI layer?** The pipeline needs browser automation (Camoufox) and local
email access (notmuch) — host-only capabilities that don't belong in a container. Running
them as MCP servers makes them composable with any MCP client (Claude Desktop, etc.).

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
- An OpenAI API key (for AI features — cover letters, summaries, prompt generation)

## Quick Start

```bash
# 1. Copy the environment file and fill in your OpenAI key
cp .env.example .env
# Open .env and set OPENAI_API_KEY=sk-...
# Everything else can stay as-is for local dev

# 2. Start the app
make up

# 3. Open the app
# http://localhost:4200
```

The first time you open the app, a setup wizard will appear. Enter a username, email, and password — this creates your admin account. The wizard only runs once.

> The first `make up` takes a few minutes while Docker builds the images and installs dependencies. Subsequent starts are fast.

## Stopping

```bash
make down
```

## Ports

| Service | URL |
|---------|-----|
| App (frontend) | http://localhost:4200 |
| API | http://localhost:8000 |
| Database | localhost:5432 (internal only) |

## Common Commands

```bash
make up          # Start the app (stops any existing containers first)
make down        # Stop everything
make logs        # Follow live logs from all services
make shell-api   # Open a shell inside the API container
make shell-db    # Open a psql shell in the database
make migrate     # Run database migrations manually
make help        # List all available commands
```

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

**Want to start fresh** — stop the app, remove the database volume, and restart:
```bash
make down
docker volume rm career_caddy_deploy_postgres_data
make up
```
