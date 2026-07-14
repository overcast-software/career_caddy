"""
Career Caddy — Dagger CI/CD Pipeline

Replaces the scattered GitHub Actions YAML across api/ and frontend/.
Run the same build/test/deploy pipeline locally and in CI.

Usage (from repo root):
  dagger -m ./dagger call build-api
  dagger -m ./dagger call build-frontend
  dagger -m ./dagger call build-ai
  dagger -m ./dagger call publish --registry-token=env:GITHUB_TOKEN --org=overcast-software --tag=latest
  dagger -m ./dagger call publish-ar --sa-key=env:GCP_SA_KEY --gcp-project=<project> --tag=latest
  dagger -m ./dagger call deploy --ssh-key=file:~/.ssh/id_ed25519 --host=your-vps-ip --app-dir=/opt/stacks/careercaddy.online --tag=latest

In GitHub Actions, call via: dagger -m ./dagger call publish ...

NOTE: Directory parameters use DefaultPath relative to the dagger/ module root.
      Defaults: ../api → api/, ../frontend → frontend/, ../agents → agents/
      Override: --src=./path/to/dir (or --api-src=, --frontend-src=, etc.)
"""

from __future__ import annotations

from typing import Annotated

import dagger
from dagger import DefaultPath, dag, function, object_type, Secret


REGISTRY = "ghcr.io"
API_IMAGE = "career_caddy_api"
FRONTEND_IMAGE = "career-caddy-frontend"
AI_IMAGE = "career_caddy_ai"

# ── Artifact Registry (AR) publish target — PACA #165 / epic #163 ──────────
# Cloud Run (the GCP dev env) pulls from Google Artifact Registry, not GHCR.
# `publish_ar()` pushes the SAME three images to AR alongside the GHCR
# `publish()` path (which is untouched). The naming contract (standardized
# 2026-07-13) is deliberate and asymmetric:
#   - AR *repository id* uses HYPHENS — GCP resource ids forbid underscores:
#         career-caddy
#   - *Image names* use UNDERSCORES, matching the GHCR source names so a
#     GHCR→AR mirror is a 1:1 path rename:
#         career_caddy_api / career_caddy_frontend / career_caddy_ai
#   - Full path: <host>/<project>/career-caddy/career_caddy_<svc>:<tag>
#     e.g. us-central1-docker.pkg.dev/<project>/career-caddy/career_caddy_api
# Host, GCP project id, repo id and tag are all args — NOTHING is hardcoded to
# the lab project. Auth is a GCP service-account key JSON passed as a Dagger
# Secret; AR accepts it as the `_json_key` docker username (see `publish_ar`).
AR_REPO_ID = "career-caddy"
AR_JSON_KEY_USERNAME = "_json_key"
# Image names are shared with GHCR (underscore form). FRONTEND_IMAGE above is
# the GHCR-historical hyphen name; AR standardizes on the underscore name.
AR_API_IMAGE = "career_caddy_api"
AR_FRONTEND_IMAGE = "career_caddy_frontend"
AR_AI_IMAGE = "career_caddy_ai"

# ── Deps-baked CI base images (PACA #8 lever A — self-hosted base image) ────
# Published siblings of the images above whose ONLY content is the heavy,
# slowly-changing toolchain + deps layer (apt + `uv sync --no-install-project`
# / `npm ci`). `_api_base` / `_frontend_base` / `_ai_base` `.from_()` these
# instead of cold-building from python:3.11-slim / node:20-slim every CI run,
# then run `uv sync --frozen` / `npm ci` on top as a self-healing reconcile.
# Pure optimization — see `_pullable` + the cold fallbacks below: a missing or
# stale base NEVER breaks CI and never tests stale deps. The pull ref uses a
# fixed BASE_ORG; a fork under another org simply misses the cache and cold-
# builds (the fallback covers it). `build_{api,frontend,ai}_base` publish them.
BASE_ORG = "overcast-software"
API_BASE_IMAGE = "career_caddy_api_base"
FRONTEND_BASE_IMAGE = "career-caddy-frontend-base"
AI_BASE_IMAGE = "career_caddy_ai_base"


@object_type
class CareerCaddy:

    # ── Shared base containers ─────────────────────────────────────────────
    # `_api_base` / `_frontend_base` / `_ai_base` produce a container with the
    # toolchain + deps installed and the source mounted, but no test/lint
    # executions yet. The lint-only and test-only functions below compose on
    # top of them so Dagger's content-addressed cache reuses the apt/uv/npm
    # steps across phases — that's what makes the lint-then-test split fast on
    # the second local pass.
    #
    # PACA #8 lever A (self-hosted base image): each base first tries to PULL a
    # deps-baked base image (`build_api_base` / `build_frontend_base` /
    # `build_ai_base` publish them to GHCR) and `.from_()`s it instead of cold-
    # building the heavy apt + `uv sync --no-install-project` / `npm ci` layer
    # every run. This matters in CI, where each GitHub-Actions run starts with a
    # COLD Dagger engine (no persistent layer cache), so the heavy layer is paid
    # on every PR today. It is a PURE OPTIMIZATION with two fail-safes:
    #   1. If the base image is missing/unpullable (bootstrap, first run, GHCR
    #      hiccup, private-without-creds), `_pullable` returns None and the base
    #      falls back to the original cold build. CI can NEVER break because a
    #      base is absent.
    #   2. The `uv sync --frozen` / `npm ci` reconcile runs on top regardless,
    #      so a STALE base self-heals to the current lockfile rather than testing
    #      old deps. Worst case = today's cold speed; never broken, never stale.

    async def _pullable(self, ref: str) -> dagger.Container | None:
        """Return a synced container from `ref`, or None if it can't be pulled.

        Forces the pull via `.sync()` so a missing image / auth / network
        failure raises here and is swallowed — callers then cold-build. The
        synced container is returned (not re-pulled), so the probe IS the pull,
        not a wasted extra round-trip.
        """
        try:
            return await dag.container().from_(ref).sync()
        except Exception:
            return None

    def _api_deps_layer(self, src: dagger.Directory) -> dagger.Container:
        """The heavy, slowly-changing api layer: python:3.11-slim + apt
        (build-essential, libpq-dev) + uv + `uv sync --frozen
        --no-install-project` (the uvloop/httptools native compiles).

        Shared verbatim by `build_api_base` (which publishes it) and by
        `_api_base`'s cold fallback (when no base is pullable) so the published
        base and the cold path are byte-identical — a current base makes the
        downstream `uv sync --frozen` reconcile a true no-op. Only reads
        pyproject.toml + uv.lock from `src`, so it is independent of the source
        strip its callers apply.
        """
        return (
            dag.container()
            .from_("python:3.11-slim")
            .with_exec(
                [
                    "sh", "-c",
                    "apt-get update && apt-get install -y --no-install-recommends "
                    "build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*",
                ]
            )
            .with_exec(["pip", "install", "uv"])
            .with_workdir("/app")
            .with_file("/app/pyproject.toml", src.file("pyproject.toml"))
            .with_file("/app/uv.lock", src.file("uv.lock"))
            .with_exec(["uv", "sync", "--frozen", "--no-install-project"])
        )

    async def _api_base(self, src: dagger.Directory) -> dagger.Container:
        src = (
            src
            .without_directory(".venv")
            .without_directory("staticfiles")
            .without_directory(".git")
        )
        # Fast path: `.from_()` the deps-baked base; cold-build fallback if it
        # can't be pulled. Both end in the same source-overlay + reconcile tail.
        prebuilt = await self._pullable(
            f"{REGISTRY}/{BASE_ORG}/{API_BASE_IMAGE}:latest"
        )
        layer = prebuilt if prebuilt is not None else self._api_deps_layer(src)
        # `uv sync --frozen` is a near no-op when the base matches the current
        # lockfile and a correct incremental install when it's stale — so this
        # single tail is BOTH the original behavior (cold path) AND the
        # self-heal (fast path). Never tests stale deps.
        return (
            layer
            .with_workdir("/app")
            .with_directory("/app", src)
            .with_exec(["uv", "sync", "--frozen"])
        )

    def _automation_base(self, src: dagger.Directory) -> dagger.Container:
        # automation/ (cc_auto) is operator-side Python: uv + pymongo +
        # pytest. No browser, no Camoufox, no postgres — its tests
        # monkeypatch `_db_or_none` so they don't hit a real Mongo.
        # Mirrors `_api_base`'s shape; the only diff is no libpq.
        src = (
            src
            .without_directory(".venv")
            .without_directory(".git")
            .without_directory("var")
        )
        return (
            dag.container()
            .from_("python:3.11-slim")
            .with_exec(
                [
                    "sh", "-c",
                    "apt-get update && apt-get install -y --no-install-recommends "
                    "make curl && rm -rf /var/lib/apt/lists/*",
                ]
            )
            .with_exec(["pip", "install", "uv"])
            .with_workdir("/app")
            .with_file("/app/pyproject.toml", src.file("pyproject.toml"))
            .with_file("/app/uv.lock", src.file("uv.lock"))
            .with_exec(["uv", "sync", "--frozen", "--no-install-project", "--group", "dev"])
            .with_directory("/app", src)
            .with_exec(["uv", "sync", "--frozen", "--group", "dev"])
        )

    def _frontend_deps_layer(self, src: dagger.Directory) -> dagger.Container:
        """The heavy, slowly-changing frontend layer: node:20-slim + the apt
        firefox-esr/xvfb/X-libs stack + `npm ci`.

        Published by `build_frontend_base` and used as `_frontend_base`'s cold
        fallback. Firefox in `node:20-slim` fails with "RenderCompositorSWGL
        failed mapping default framebuffer" under `-headless` because there's
        no /dev/dri; xvfb-run gives it a virtual framebuffer and xauth supplies
        the cookie. Only reads package.json + package-lock.json from `src`.
        """
        return (
            dag.container()
            .from_("node:20-slim")
            .with_exec(
                [
                    "sh", "-c",
                    "apt-get update && apt-get install -y --no-install-recommends "
                    "firefox-esr xvfb xauth "
                    "libpci3 libgl1 libegl1 libdbus-glib-1-2 "
                    "libgtk-3-0 libasound2 "
                    "&& rm -rf /var/lib/apt/lists/*",
                ]
            )
            .with_workdir("/app")
            .with_file("/app/package.json", src.file("package.json"))
            .with_file("/app/package-lock.json", src.file("package-lock.json"))
            .with_env_variable("CI", "true")
            .with_env_variable("MOZ_HEADLESS", "1")
            .with_exec(["npm", "ci"])
        )

    async def _frontend_base(self, src: dagger.Directory) -> dagger.Container:
        src = (
            src
            .without_directory("node_modules")
            .without_directory("dist")
            .without_directory(".git")
        )
        prebuilt = await self._pullable(
            f"{REGISTRY}/{BASE_ORG}/{FRONTEND_BASE_IMAGE}:latest"
        )
        if prebuilt is not None:
            # Fast path: the baked apt firefox/X-libs stack (the genuinely heavy
            # layer) + node_modules arrive as a registry pull. Re-run `npm ci`
            # against the CURRENT package-lock so a stale base self-heals
            # (re-resolves) rather than testing old node_modules. NOTE: unlike
            # `uv sync --frozen`, `npm ci` always does a clean reinstall, so the
            # frontend win is the baked apt layer + the parallel base-image pull,
            # not skipping npm ci (a lockfile-cmp conditional could skip it when
            # unchanged — left as a future optimization, see PR notes). CI=true /
            # MOZ_HEADLESS=1 come baked in from the published base.
            return (
                prebuilt
                .with_workdir("/app")
                .with_directory("/app", src)
                .with_exec(["npm", "ci"])
            )
        # Cold fallback — byte-identical to the pre-base build (apt + npm ci,
        # then overlay the source over the installed node_modules; `src` already
        # excludes node_modules so the install survives). CI never breaks when
        # the base is absent.
        return self._frontend_deps_layer(src).with_directory("/app", src)

    def _ai_deps_layer(self, src: dagger.Directory) -> dagger.Container:
        """The heavy, slowly-changing agents/ test layer: python:3.13-slim +
        apt (build-essential) + uv + `uv sync --frozen --no-install-project`
        (FULL deps incl. dev/pytest — this base serves `test_ai`).

        Published by `build_ai_base` and used as `_ai_base`'s cold fallback. No
        Camoufox — the AI CI image excludes the ~700 MB browser. Only reads
        pyproject.toml + uv.lock from `src`, and never copies secrets.yml.
        """
        return (
            dag.container()
            .from_("python:3.13-slim")
            .with_exec(
                [
                    "sh", "-c",
                    "apt-get update && apt-get install -y --no-install-recommends "
                    "build-essential curl && rm -rf /var/lib/apt/lists/*",
                ]
            )
            .with_exec(["pip", "install", "uv"])
            .with_workdir("/app")
            .with_file("/app/pyproject.toml", src.file("pyproject.toml"))
            .with_file("/app/uv.lock", src.file("uv.lock"))
            .with_exec(["uv", "sync", "--frozen", "--no-install-project"])
        )

    async def _ai_base(self, src: dagger.Directory) -> dagger.Container:
        """Deps-baked (or cold-fallback) base for the agents/ test suite.
        Mirrors `_api_base`: pull the baked base else cold-build, then `uv sync
        --frozen` over the full source as a self-healing reconcile."""
        src = (
            src
            .without_directory(".venv")
            .without_directory("screenshots")
            .without_file("secrets.yml")
            .without_directory(".git")
        )
        prebuilt = await self._pullable(
            f"{REGISTRY}/{BASE_ORG}/{AI_BASE_IMAGE}:latest"
        )
        layer = prebuilt if prebuilt is not None else self._ai_deps_layer(src)
        return (
            layer
            .with_workdir("/app")
            .with_directory("/app", src)
            .with_exec(["uv", "sync", "--frozen"])
        )

    # ── Lint-only (cheap, fail-fast) ───────────────────────────────────────

    @function
    async def lint_api(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../api")],
    ) -> dagger.Container:
        """Ruff + bandit on the api source. No db, no test suite."""
        return (
            (await self._api_base(src))
            .with_exec(["uv", "run", "ruff", "check", "."])
            .with_exec(["uv", "run", "bandit", "-r", ".", "-x", "*/migrations/*,./.venv/*", "-ll"])
        )

    @function
    async def lint_frontend(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../frontend")],
    ) -> dagger.Container:
        """eslint + prettier + ember-template-lint + stylelint. No tests."""
        return (await self._frontend_base(src)).with_exec(["npm", "run", "lint"])

    @function
    async def lint_automation(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../automation")],
    ) -> dagger.Container:
        """Ruff check on the automation (cc_auto) source. Uses cc_auto's
        Makefile entry point so cc-auto agent's contract stays canonical:
        whatever `make lint` runs locally is what CI runs."""
        return self._automation_base(src).with_exec(["make", "lint"])

    # ── Tests-only (slow) ──────────────────────────────────────────────────

    @function
    async def test_api(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../api")],
    ) -> dagger.Container:
        """Django test suite against a postgres sidecar. Skips lint."""
        pg = (
            dag.container()
            .from_("postgres:18")
            .with_env_variable("POSTGRES_DB", "job_hunting_ci")
            .with_env_variable("POSTGRES_USER", "postgres")
            .with_env_variable("POSTGRES_PASSWORD", "postgres")
            .with_exposed_port(5432)
            .as_service()
        )
        return (
            (await self._api_base(src))
            .with_service_binding("db", pg)
            .with_env_variable(
                "DATABASE_URL", "postgresql://postgres:postgres@db:5432/job_hunting_ci"
            )
            .with_env_variable("SECRET_KEY", "ci-test-secret-not-for-production")
            .with_env_variable("DEBUG", "True")
            # --keepdb skips DROP DATABASE at the end (the postgres sidecar
            # health-checker can still hold a connection, intermittently
            # failing teardown). Fresh container each run, no state leak.
            #
            # Tee output to /test.log so the assertion step below can verify
            # the canonical success markers. pipefail propagates manage.py's
            # exit through `tee` (which always exits 0).
            .with_exec([
                "bash", "-c",
                "set -o pipefail; "
                "uv run python manage.py test -v 1 --keepdb --noinput 2>&1 "
                "| tee /test.log",
            ])
            # Belt-and-suspenders: even if the runner ever exits 0 with
            # zero tests collected or swallowed failures, require the
            # canonical success markers in the log. Tally #9/#13/#14/#19 —
            # this assertion closes the green-but-broken gap.
            #
            # Cat the log first so `dagger call test-api stdout` returns
            # the test output (otherwise the grep-q exec is silent and
            # downstream filters have nothing to chew on).
            .with_exec([
                "sh", "-c",
                "cat /test.log; "
                "grep -qE '^Ran [1-9][0-9]* test' /test.log "
                "&& grep -qE '^OK( |$)' /test.log",
            ])
        )

    @function
    async def test_frontend(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../frontend")],
    ) -> dagger.Container:
        """Ember QUnit suite under xvfb. Skips lint."""
        return (
            (await self._frontend_base(src))
            # Tee TAP output to /tap.log so the assertion step below can
            # verify the summary lines. pipefail propagates `ember test`'s
            # exit past `tee`.
            .with_exec([
                "bash", "-c",
                "set -o pipefail; "
                "xvfb-run -a npm run test:ember 2>&1 | tee /tap.log",
            ])
            # Belt-and-suspenders: even if the runner ever exits 0 with
            # zero passes or non-zero fails, require the canonical TAP
            # summary in the log. Tally #9/#13/#14/#19.
            #
            # Cat the log first so `dagger call test-frontend stdout`
            # returns the TAP (otherwise the grep-q exec is silent and
            # downstream filters have nothing to chew on).
            .with_exec([
                "sh", "-c",
                "cat /tap.log; "
                "grep -qE '^# fail +0$' /tap.log "
                "&& grep -qE '^# pass +[1-9]' /tap.log",
            ])
        )

    @function
    async def test_automation(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../automation")],
    ) -> dagger.Container:
        """pytest against automation (cc_auto). Tests monkeypatch the
        Mongo client — no postgres / mongo sidecar required."""
        return (
            self._automation_base(src)
            # Tee pytest output to /test.log so the assertion below can
            # verify the canonical "N passed in Ms" summary. pipefail
            # propagates pytest's exit through `tee`.
            .with_exec([
                "bash", "-c",
                "set -o pipefail; "
                "make test 2>&1 | tee /test.log",
            ])
            # Belt-and-suspenders: require the canonical pytest success
            # summary in the log. Guards against "exit 0 with zero tests
            # collected" (would not match `\d+ passed`) and against any
            # failed/error lines slipping through. Matches the api +
            # frontend lint-then-test split's assertion style.
            #
            # Cat the log first so `dagger call test-automation stdout`
            # returns the test output (otherwise the grep-q exec is
            # silent and downstream filters have nothing to chew on).
            .with_exec([
                "sh", "-c",
                "cat /test.log; "
                "grep -qE '[0-9]+ passed' /test.log "
                "&& ! grep -qE '[0-9]+ failed' /test.log "
                "&& ! grep -qE '[0-9]+ error' /test.log",
            ])
        )

    # ── Combined (kept for parent-Deploy + workflows that call them) ──────

    @function
    async def build_api(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../api")],
    ) -> dagger.Container:
        """Lint + test the api in one shot. Used by .github/workflows.

        Local `make ci` uses the split lint-api / test-api functions for
        fail-fast. This combined function stays for the parent Deploy
        workflow which invokes it directly.
        """
        # Compose: run lint steps then test steps on the same base.
        # Reuses the cached api_base; serially adds lint then test+assert.
        pg = (
            dag.container()
            .from_("postgres:18")
            .with_env_variable("POSTGRES_DB", "job_hunting_ci")
            .with_env_variable("POSTGRES_USER", "postgres")
            .with_env_variable("POSTGRES_PASSWORD", "postgres")
            .with_exposed_port(5432)
            .as_service()
        )
        return (
            (await self._api_base(src))
            .with_exec(["uv", "run", "ruff", "check", "."])
            .with_exec(["uv", "run", "bandit", "-r", ".", "-x", "*/migrations/*,./.venv/*", "-ll"])
            .with_service_binding("db", pg)
            .with_env_variable(
                "DATABASE_URL", "postgresql://postgres:postgres@db:5432/job_hunting_ci"
            )
            .with_env_variable("SECRET_KEY", "ci-test-secret-not-for-production")
            .with_env_variable("DEBUG", "True")
            .with_exec([
                "bash", "-c",
                "set -o pipefail; "
                "uv run python manage.py test -v 1 --keepdb --noinput 2>&1 "
                "| tee /test.log",
            ])
            .with_exec([
                "sh", "-c",
                "grep -qE '^Ran [1-9][0-9]* test' /test.log "
                "&& grep -qE '^OK( |$)' /test.log",
            ])
        )

    @function
    async def build_frontend(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../frontend")],
    ) -> dagger.Container:
        """Lint + test the frontend in one shot. Used by .github/workflows."""
        return (
            (await self._frontend_base(src))
            .with_exec(["npm", "run", "lint"])
            .with_exec([
                "bash", "-c",
                "set -o pipefail; "
                "xvfb-run -a npm run test:ember 2>&1 | tee /tap.log",
            ])
            .with_exec([
                "sh", "-c",
                "grep -qE '^# fail +0$' /tap.log "
                "&& grep -qE '^# pass +[1-9]' /tap.log",
            ])
        )

    @function
    async def build_ai(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../agents")],
    ) -> dagger.Container:
        """Build the AI agent image (Python 3.13, no Camoufox).

        Camoufox (~700 MB) is excluded. Browser scraping runs on a separate
        device (Pi) via the hold-poller, not on the VPS.
        """
        src = (
            src
            .without_directory(".venv")
            .without_directory("screenshots")
            .without_file("secrets.yml")
            .without_directory(".git")
        )

        return (
            dag.container()
            .from_("python:3.13-slim")
            .with_exec(
                [
                    "sh", "-c",
                    "apt-get update && apt-get install -y --no-install-recommends "
                    "build-essential curl && rm -rf /var/lib/apt/lists/*",
                ]
            )
            .with_exec(["pip", "install", "uv"])
            .with_workdir("/app")
            .with_file("/app/pyproject.toml", src.file("pyproject.toml"))
            .with_file("/app/uv.lock", src.file("uv.lock"))
            .with_exec(["uv", "sync", "--frozen", "--no-dev", "--no-install-project"])
            .with_directory("/app", src)
            .with_exec(["uv", "sync", "--frozen", "--no-dev"])
        )

    @function
    async def test_ai(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../agents")],
    ) -> dagger.Container:
        """Run AI test suite (toolsets, api_tools, public_server security)."""
        return (
            (await self._ai_base(src))
            .with_env_variable("LOGFIRE_SEND_TO_LOGFIRE", "false")
            .with_exec(["uv", "run", "pytest", "tests/", "-v"])
        )

    # ── Deps-baked CI base image publisher (PACA #8 lever A) ───────────────
    # Publish the heavy deps layer so CI `.from_()`s it instead of cold-
    # building. Rebuilt OUT OF BAND by .github/workflows/rebuild-base-images.yml
    # (nightly + on a submodule-pin push + manual) — NEVER in the deploy-gating
    # path. Staleness is safe (see `_pullable` + the `uv sync --frozen` / `npm
    # ci` reconcile), so the rebuild trigger can be coarse without risking CI.
    # These DO NOT touch `publish()` (lever B) or the Dockerfiles.

    async def _publish_base(
        self,
        layer: dagger.Container,
        ref: str,
        username: str,
        registry_token: Secret,
    ) -> str:
        """Auth + publish a deps-baked base container to `ref`."""
        return await (
            layer
            .with_registry_auth(REGISTRY, username, registry_token)
            .publish(ref)
        )

    async def _build_publish(
        self,
        src: dagger.Directory,
        ref: str,
        username: str,
        registry_token: Secret,
        build_args: list | None,
        build_kwargs: dict,
    ) -> str:
        """Cold-build `src` and push it to `ref`. Returns the pushed ref."""
        kwargs = dict(build_kwargs)
        if build_args:
            kwargs["build_args"] = build_args
        return await (
            src
            .docker_build(**kwargs)
            .with_registry_auth(REGISTRY, username, registry_token)
            .publish(ref)
        )

    @function
    async def build_api_base(
        self,
        registry_token: Secret,
        src: Annotated[dagger.Directory, DefaultPath("../api")],
        org: str = "overcast-software",
        tag: str = "latest",
        registry_username: str = "",
    ) -> str:
        """Build + publish the api deps-baked base image to GHCR.

        Bakes apt (build-essential, libpq-dev) + uv + `uv sync --frozen
        --no-install-project` (the uvloop/httptools native compiles) so
        `_api_base` can `.from_()` it. Pure optimization: `_api_base` cold-
        builds when this image is absent and reconciles with `uv sync --frozen`
        on top, so a missing/stale base is always safe. Only pyproject.toml +
        uv.lock + installed deps land in the image — no source, no .git.

        Args:
            registry_token: GitHub token with packages:write permission
            org: GitHub organization (image path)
            tag: Image tag (the CI pull ref is `:latest`)
            registry_username: GHCR actor username (defaults to org)
        """
        username = registry_username or org
        ref = f"{REGISTRY}/{org}/{API_BASE_IMAGE}:{tag}"
        return await self._publish_base(
            self._api_deps_layer(src), ref, username, registry_token
        )

    @function
    async def build_frontend_base(
        self,
        registry_token: Secret,
        src: Annotated[dagger.Directory, DefaultPath("../frontend")],
        org: str = "overcast-software",
        tag: str = "latest",
        registry_username: str = "",
    ) -> str:
        """Build + publish the frontend deps-baked base image to GHCR.

        Bakes the apt firefox-esr/xvfb/X-libs stack + `npm ci` so
        `_frontend_base` can `.from_()` it. `_frontend_base` re-runs `npm ci` on
        top (clean reinstall) so a stale base self-heals; CI cold-builds when
        this image is absent. Only package.json + package-lock.json + installed
        node_modules land in the image — no source, no .git.
        """
        username = registry_username or org
        ref = f"{REGISTRY}/{org}/{FRONTEND_BASE_IMAGE}:{tag}"
        return await self._publish_base(
            self._frontend_deps_layer(src), ref, username, registry_token
        )

    @function
    async def build_ai_base(
        self,
        registry_token: Secret,
        src: Annotated[dagger.Directory, DefaultPath("../agents")],
        org: str = "overcast-software",
        tag: str = "latest",
        registry_username: str = "",
    ) -> str:
        """Build + publish the agents/ test deps-baked base image to GHCR.

        Bakes apt (build-essential) + uv + `uv sync --frozen
        --no-install-project` (full deps incl. dev/pytest) so `_ai_base` (used
        by `test_ai`) can `.from_()` it. Cold fallback + `uv sync --frozen`
        reconcile keep a missing/stale base safe. secrets.yml is never copied.
        """
        username = registry_username or org
        ref = f"{REGISTRY}/{org}/{AI_BASE_IMAGE}:{tag}"
        return await self._publish_base(
            self._ai_deps_layer(src), ref, username, registry_token
        )

    async def _retag(
        self,
        repo: str,
        prev_tag: str,
        tag: str,
        username: str,
        registry_token: Secret,
    ) -> str:
        """Copy `{repo}:{prev_tag}` → `{repo}:{tag}` in GHCR without rebuilding.

        Uses crane (server-side manifest copy — no image pull/push of layers,
        and platform-agnostic: it copies whatever the prev manifest was). The
        `:debug` image is required because `crane auth login --password-stdin`
        needs a shell to read the mounted token from stdin; the default crane
        image is distroless with no shell.

        Forces execution via `.sync()` so any failure (missing prev image,
        auth error, network) raises — the caller catches and falls back to a
        cold build, so a tag is NEVER left stale or missing.
        """
        src_ref = f"{repo}:{prev_tag}"
        dst_ref = f"{repo}:{tag}"
        await (
            dag.container()
            .from_("gcr.io/go-containerregistry/crane:debug")
            .with_mounted_secret("/run/secrets/ghcr_token", registry_token)
            .with_exec([
                "sh", "-c",
                f"crane auth login {REGISTRY} -u {username} --password-stdin "
                f"< /run/secrets/ghcr_token "
                f"&& crane copy {src_ref} {dst_ref}",
            ])
            .sync()
        )
        return dst_ref

    @function
    async def publish(
        self,
        registry_token: Secret,
        api_src: Annotated[dagger.Directory, DefaultPath("../api")],
        frontend_src: Annotated[dagger.Directory, DefaultPath("../frontend")],
        ai_src: Annotated[dagger.Directory, DefaultPath("../agents")],
        org: str = "overcast-software",
        tag: str = "latest",
        registry_username: str = "",
        platform: str = "",
        frontend_api_host: str = "",
        prev_tag: str = "",
        changed: str = "api,frontend,ai",
    ) -> list[str]:
        """Build changed images, retag unchanged ones, push to GHCR.

        On a parent-main push that only bumped some submodule pins, the
        unchanged submodules' images are byte-identical to the previous
        deploy, so we copy (`crane copy`) the already-published
        `{repo}:{prev_tag}` to `{repo}:{tag}` instead of cold-rebuilding —
        keeping the single parent-SHA `IMAGE_TAG` contract (no
        docker-compose.prod.yml change). Returns the list of resulting refs.

        FAIL SAFE — an image reaches `:{tag}` only by (a) a fresh build, or
        (b) a retag from a prev tag whose pin was byte-identical. Two layers:
          1. `prev_tag == ""` forces a build for every image (the all-zeros /
             first-push / force-push guard sets this in the workflow).
          2. `changed` defaults to all three images, so any mis-call or empty
             arg reproduces today's build-everything behavior.
          3. If a retag throws for ANY reason (prev image missing, auth,
             network) the per-image path falls back to a cold build.
        Never stale, never missing.

        Args:
            registry_token: GitHub token with packages:write permission
            org: GitHub organization (used in image path)
            tag: Image tag (use git SHA for immutable tags)
            registry_username: GitHub actor username for GHCR auth (defaults to org)
            platform: Target platform (e.g. "linux/arm64"); empty = engine
                native (amd64 in CI). Use with QEMU for cross-builds.
            frontend_api_host: API origin baked into the frontend production
                build. Default is empty → same-origin (SPA emits /api/v1/...;
                outer proxy routes /api/* to the api container). Pass a full
                origin only for explicit cross-origin deployments.
            prev_tag: Image tag of the previous deploy (the parent SHA before
                this push). Empty → build every image (safe default).
            changed: Comma list of image names that changed this push
                (api / frontend / ai). Defaults to all three. The workflow
                maps the changed submodule gitlinks (api→api, frontend→
                frontend, agents→ai) into this list.
        """
        username = registry_username or org
        api_repo = f"{REGISTRY}/{org}/{API_IMAGE}"
        frontend_repo = f"{REGISTRY}/{org}/{FRONTEND_IMAGE}"
        ai_repo = f"{REGISTRY}/{org}/{AI_IMAGE}"

        changed_set = {c.strip() for c in changed.split(",") if c.strip()}

        build_kwargs: dict = {}
        if platform:
            build_kwargs["platform"] = dagger.Platform(platform)

        async def resolve(
            name: str,
            src: dagger.Directory,
            repo: str,
            build_args: list | None,
        ) -> str:
            ref = f"{repo}:{tag}"
            # Build when there is no previous tag to copy from, or when this
            # image's pin actually changed this push.
            if not prev_tag or name in changed_set:
                return await self._build_publish(
                    src, ref, username, registry_token, build_args, build_kwargs
                )
            # Unchanged pin → retag prev→tag; fall back to a build on ANY
            # failure so the tag is never left stale or missing.
            try:
                return await self._retag(
                    repo, prev_tag, tag, username, registry_token
                )
            except Exception:
                return await self._build_publish(
                    src, ref, username, registry_token, build_args, build_kwargs
                )

        pushed_api = await resolve("api", api_src, api_repo, None)
        pushed_frontend = await resolve(
            "frontend",
            frontend_src,
            frontend_repo,
            [dagger.BuildArg("API_HOST", frontend_api_host)],
        )
        # AI image: build without Camoufox (browser runs on Pi, not VPS)
        pushed_ai = await resolve(
            "ai",
            ai_src,
            ai_repo,
            [dagger.BuildArg("INSTALL_CAMOUFOX", "false")],
        )

        return [pushed_api, pushed_frontend, pushed_ai]

    # ── Artifact Registry publish (PACA #165) ──────────────────────────────
    # Parallel path to `publish()` above. Builds the same three images and
    # pushes them to Google Artifact Registry so Cloud Run (the GCP dev env)
    # can pull them. GHCR `publish()` is untouched. This deliberately does NOT
    # inherit the GHCR retag-unchanged optimization: AR is a fresh registry
    # with no prior tags to copy from, so every requested image is built. The
    # `changed` arg still lets a caller scope the push to a subset.

    async def _build_publish_ar(
        self,
        src: dagger.Directory,
        ref: str,
        host: str,
        sa_key: Secret,
        build_args: list | None,
        build_kwargs: dict,
    ) -> str:
        """Cold-build `src` and push it to `ref` in Artifact Registry.

        AR authenticates a docker push with the GCP service-account key JSON
        used as the password under the fixed `_json_key` username — no gcloud
        binary or cred-helper needed inside the build container. Returns the
        pushed ref.
        """
        kwargs = dict(build_kwargs)
        if build_args:
            kwargs["build_args"] = build_args
        return await (
            src
            .docker_build(**kwargs)
            .with_registry_auth(host, AR_JSON_KEY_USERNAME, sa_key)
            .publish(ref)
        )

    @function
    async def publish_ar(
        self,
        sa_key: Secret,
        gcp_project: str,
        api_src: Annotated[dagger.Directory, DefaultPath("../api")],
        frontend_src: Annotated[dagger.Directory, DefaultPath("../frontend")],
        ai_src: Annotated[dagger.Directory, DefaultPath("../agents")],
        host: str = "us-central1-docker.pkg.dev",
        repo_id: str = AR_REPO_ID,
        tag: str = "latest",
        platform: str = "",
        frontend_api_host: str = "",
        changed: str = "api,frontend,ai",
    ) -> list[str]:
        """Build the api/frontend/ai images and push them to Artifact Registry.

        Mirrors GHCR `publish()` but targets AR (Cloud Run's source registry).
        Every requested image is built — AR has no prior tag to retag from —
        while `changed` lets a caller scope the push to a subset.

        Naming contract (see AR_* constants): the AR repository id is
        `career-caddy` (hyphens — GCP ids forbid underscores) and the image
        names keep the GHCR underscore form (`career_caddy_api` /
        `career_caddy_frontend` / `career_caddy_ai`). Full path:
        `<host>/<gcp_project>/<repo_id>/career_caddy_<svc>:<tag>`.

        Auth: `sa_key` is a GCP service-account key JSON with the
        Artifact Registry Writer role, passed as a Dagger Secret. It is used
        as the docker password under the `_json_key` username — no gcloud in
        the container.
          - CI supplies it from a repo/environment secret, e.g.
                --sa-key=env:GCP_SA_KEY
            where GCP_SA_KEY holds the raw JSON key (or file:/path/to/key.json).
          - A local run authenticates the same way with a downloaded key:
                dagger -m ./dagger call publish-ar \\
                  --sa-key=file:$HOME/gcp-ar-writer.json \\
                  --gcp-project=cc-gcp-lab-dkh --tag=latest
            (Alternatively `gcloud auth configure-docker <host>` + ADC works
            for a raw docker push, but the Dagger-native path is the SA key so
            CI and local behave identically.)

        Args:
            sa_key: GCP service-account key JSON (Artifact Registry Writer).
            gcp_project: GCP project id that owns the AR repository.
            host: AR host, e.g. "us-central1-docker.pkg.dev".
            repo_id: AR repository id (hyphens). Defaults to "career-caddy".
            tag: Image tag (use a git SHA for immutable tags).
            platform: Target platform (e.g. "linux/arm64"); empty = engine
                native. Use with QEMU for cross-builds.
            frontend_api_host: API origin baked into the frontend production
                build. Empty = same-origin (SPA emits /api/v1/...).
            changed: Comma list of image names to build+push (api / frontend /
                ai). Defaults to all three.
        """
        base = f"{host}/{gcp_project}/{repo_id}"
        api_repo = f"{base}/{AR_API_IMAGE}"
        frontend_repo = f"{base}/{AR_FRONTEND_IMAGE}"
        ai_repo = f"{base}/{AR_AI_IMAGE}"

        changed_set = {c.strip() for c in changed.split(",") if c.strip()}

        build_kwargs: dict = {}
        if platform:
            build_kwargs["platform"] = dagger.Platform(platform)

        async def resolve(
            name: str,
            src: dagger.Directory,
            repo: str,
            build_args: list | None,
        ) -> str | None:
            if name not in changed_set:
                return None
            return await self._build_publish_ar(
                src, f"{repo}:{tag}", host, sa_key, build_args, build_kwargs
            )

        pushed = []
        for ref in (
            await resolve("api", api_src, api_repo, None),
            await resolve(
                "frontend",
                frontend_src,
                frontend_repo,
                [dagger.BuildArg("API_HOST", frontend_api_host)],
            ),
            await resolve(
                "ai",
                ai_src,
                ai_repo,
                [dagger.BuildArg("INSTALL_CAMOUFOX", "false")],
            ),
        ):
            if ref is not None:
                pushed.append(ref)

        return pushed

    @function
    async def deploy(
        self,
        ssh_key: Secret,
        host: str,
        compose_file: Annotated[dagger.File, DefaultPath("../docker-compose.prod.yml")],
        app_dir: str = "/opt/stacks/careercaddy.online",
        tag: str = "latest",
        ssh_user: str = "deploy",
    ) -> str:
        """Deploy to VPS: copy docker-compose.prod.yml, pull images, restart services.

        Args:
            ssh_key: Private SSH key for the server
            host: VPS hostname or IP
            app_dir: Directory on the server where docker-compose.prod.yml lives
            tag: Image tag to deploy
            ssh_user: SSH user on the server
        """
        return await (
            dag.container()
            .from_("alpine:3.19")
            .with_exec(["apk", "add", "--no-cache", "openssh-client", "docker-cli"])
            .with_mounted_secret("/run/secrets/ssh_key", ssh_key)
            .with_exec(["sh", "-c", "mkdir -p /root/.ssh && chmod 700 /root/.ssh && { tr -d '\\r' < /run/secrets/ssh_key; echo; } > /root/.ssh/id_ed25519 && chmod 600 /root/.ssh/id_ed25519 && ssh-keygen -y -f /root/.ssh/id_ed25519 > /root/.ssh/id_ed25519.pub"])
            .with_exec(
                [
                    "sh",
                    "-c",
                    f"ssh-keyscan -H {host} >> /root/.ssh/known_hosts 2>/dev/null",
                ]
            )
            .with_file("/workspace/docker-compose.prod.yml", compose_file)
            .with_exec(
                [
                    "scp",
                    "-i", "/root/.ssh/id_ed25519",
                    "/workspace/docker-compose.prod.yml",
                    f"{ssh_user}@{host}:{app_dir}/docker-compose.prod.yml",
                ]
            )
            .with_exec(
                [
                    "ssh",
                    "-i", "/root/.ssh/id_ed25519",
                    "-o", "StrictHostKeyChecking=no",
                    f"{ssh_user}@{host}",
                    f"set -ex; "
                    f"cd {app_dir}; "
                    f"grep -q '^IMAGE_TAG=' .env && sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG={tag}/' .env || echo 'IMAGE_TAG={tag}' >> .env; "
                    f"docker compose -f docker-compose.prod.yml pull; "
                    f"docker compose -f docker-compose.prod.yml down --remove-orphans; "
                    f"docker compose -f docker-compose.prod.yml up -d --remove-orphans; "
                    # Reclaim disk: prune unused images (including OLD per-SHA
                    # tags from previous deploys, not just dangling ones),
                    # stopped containers, and unused networks. Equivalent to
                    # the manual `docker system prune -a` the operator was
                    # running by hand. Volumes are intentionally excluded —
                    # the Postgres data volume must survive.
                    f"docker system prune -a -f",
                ]
            )
            .stdout()
        )
