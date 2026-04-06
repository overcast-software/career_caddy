# Career Caddy

A personal job hunt dashboard. Track applications, store job postings, manage your resume, and generate AI-assisted cover letters and application answers.

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
