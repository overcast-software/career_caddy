# Contributing to Career Caddy

Thanks for taking a look. This file is meant to get you from `git clone` to a
running stack and a merged pull request **without needing anything the
maintainers have that you don't**.

Career Caddy is GPL-3.0. By contributing you agree your work ships under that
licence.

---

## What you need

- **Docker + Docker Compose** — the whole stack runs in containers; you don't
  need Python, Node, or Postgres on your host.
- **An LLM API key** — `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`). Most of the
  app works without one; the AI features (scoring, cover letters, answer
  drafting, summaries) don't.
- **Git with submodule support.** This is a submodule monorepo — see below.

---

## Clone (mind the submodules)

```
git clone --recurse-submodules https://github.com/overcast-software/career_caddy.git
cd career_caddy
```

Already cloned without them?

```
git submodule update --init --recursive
```

If `api/` or `frontend/` look empty, that's the missing step.

---

## Run it locally

```
cp .env.example .env
# set OPENAI_API_KEY. Leave DB_PASSWORD=postgres and SECRET_KEY blank —
# compose supplies a dev fallback for SECRET_KEY.

docker compose up --build
```

Wait for the services to report healthy, then open **http://localhost:4200**.

On a fresh database the frontend routes to `/setup`, a one-time wizard that
creates the first admin user via `POST /api/v1/initialize/`. After that
`/setup` is permanently disabled.

First start is slow — Tailwind compiles on boot. That's normal, not a hang.

Useful extras:

```
make demo-data     # seed a demo user + data (run after the stack is up)
make list          # what's running, and on which ports
make doctor        # check your local environment
make help          # every target
```

---

## Repository layout

One parent repo pinning several independently deployable submodules. Each has
its own `CLAUDE.md` with deeper, surface-specific notes.

| path | what it is |
|---|---|
| `api/` | Django + DRF backend serving JSON:API |
| `frontend/` | Ember.js SPA, **and** the `career-caddy-sender` browser extension |
| `agents/` | service-side AI: browser scraper, the scrape state machine, MCP servers |
| `automation/` | operator-side toolkit (email triage, orchestration). Talks to the api over HTTP only |
| `deploy/` | reference deploy config — Terraform for Cloud Run, plus a one-box compose setup |
| `e2e/` | Cypress smoke suite |

The split between `agents/` and `automation/` is *who it serves*: `agents/`
runs as containers for everyone, `automation/` runs on a single operator's own
machines. Service for everyone → `agents/`. Operator for one user →
`automation/`.

---

## Running tests

```
make test-api          # Django tests
make test-frontend     # Ember QUnit
make test-automation   # pytest
make ci                # the full gate: lint + test across api, frontend, automation
```

`make ci` runs through [Dagger](https://dagger.io) in its own containers, which
is what CI runs too — so a green `make ci` locally is a strong signal.

**Read the output, not just the exit code.** Grep for `Ran N tests` (api) and
`# pass N` (frontend). This has bitten people.

### Iterating on api tests

The full Django suite is ~1700 tests and slow. While iterating, run just the
module you're touching:

```
make test-api PATHS="job_hunting.tests.test_your_module"
```

Run the full suite once before you open the PR, not on every save.

### The browser extension is not covered by lint or tests

`frontend/public/extensions/` is **excluded** from prettier and eslint, and has
no test suite — it ships as-is. The real gate is:

```
node --check frontend/public/extensions/career-caddy-sender/popup.js
node --check frontend/public/extensions/career-caddy-sender/background.js
```

plus loading it unpacked and clicking through. A green frontend CI says
nothing about extension changes. See `frontend/CLAUDE.md`.

---

## Conventions worth knowing before you write code

- **JSON:API everywhere.** `Content-Type: application/vnd.api+json`. Attribute
  keys are **snake_case** — this codebase deliberately does *not* dasherize.
- **Dedupe first on any JobPost write path.** The same role posted to LinkedIn,
  Greenhouse and Lever must collapse to one canonical record. If you add a way
  to create a JobPost, it goes through the dedupe pipeline
  (`api/job_hunting/models/job_post_dedupe.py`).
- **New database tables need discussion first.** Open an issue before writing a
  migration that adds a model. Prefer extra columns, a JSONB blob, or a status
  field on something that already exists. The data model is deliberately kept
  small and readable.
- **Auth has two shapes.** The frontend uses a JWT (`Authorization: Bearer
  <jwt>`, auto-refreshed). Agents and automation use long-lived API keys with a
  `jh_` prefix on the *same* header. There is no `Api-Key` scheme; sending one
  gets a 401 that looks confusingly like an empty result.
- **Frontend HTTP calls** should use one of the four documented patterns in
  `frontend/CLAUDE.md` rather than raw `fetch`, except for file upload/download
  and pre-auth flows.

---

## Submitting a change

Branch off `main`; one concern per branch.

**If your change touches a submodule** (which most do), the order matters:

1. Commit and open a PR **in the submodule repo** (`career_caddy_api`,
   `career_caddy_frontend`, …). That's where the code review happens.
2. Once it merges, the **parent** repo gets a small commit bumping the
   submodule pointer to the merged SHA.

Maintainers handle step 2 — you generally only need to open the submodule PR.
Say in the PR description which submodule and what it depends on.

Please include:

- what changed and **why** — the reasoning is more useful than the diff
- how you verified it (commands you ran, output you saw)
- anything you *couldn't* verify, said plainly

Never commit `.env` files or secrets.

---

## Where the knowledge lives

**In this repo.** Each submodule's `CLAUDE.md` carries the architecture,
conventions and gotchas for that surface. If you find something that isn't
written down, that's a bug in the docs — please say so, or send a patch.

**On the project board.** Planned and in-flight work lives on a board at
[plans.careercaddy.dev](https://plans.careercaddy.dev), referenced throughout
the docs and commit messages by ticket ids like `CC-123` or `CCEXT-26`. It is
being opened up for public read access — if it still asks you to log in, that
rollout hasn't landed yet. Nothing in this repo should *require* it: a ticket
id in a commit is context, not a prerequisite.

The maintainers also run a private memory service for their own agent
workflow, which you'll see mentioned in some `CLAUDE.md` files. **You don't
need it, and nothing here should depend on it.** If you hit a doc that only
makes sense with maintainer tooling, that's the doc's fault — open an issue.

Human-facing product documentation lives at
[wiki.careercaddy.online](https://wiki.careercaddy.online) and in-app under
`/docs`.

---

## Self-hosting

Career Caddy is built to be self-hosted; `careercaddy.online` is just the
maintainers' instance. `deploy/` holds the reference configuration — Terraform
for Google Cloud Run, and a single-box Docker Compose setup with Caddy. The
compose path in this file is enough to run it for yourself.

Note that the browser extension currently hardcodes the maintainers' instance
origin, so it does not yet work against a self-hosted deployment without
editing `popup.js`. Making that configurable is tracked work.
