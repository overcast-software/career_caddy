"""
Career Caddy — Dagger CI/CD Pipeline

Replaces the scattered GitHub Actions YAML across api/ and frontend/.
Run the same build/test/deploy pipeline locally and in CI.

Usage (from repo root):
  dagger -m ./dagger call build-api
  dagger -m ./dagger call build-frontend
  dagger -m ./dagger call build-ai
  dagger -m ./dagger call publish --registry-token=env:GITHUB_TOKEN --org=overcast-software --tag=latest
  dagger -m ./dagger call deploy --ssh-key=file:~/.ssh/id_ed25519 --host=your-vps-ip --app-dir=/home/oldbones/Projects/career_caddy --tag=latest

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


@object_type
class CareerCaddy:

    # ── Shared base containers ─────────────────────────────────────────────
    # `_api_base` and `_frontend_base` produce a container with toolchain +
    # deps installed and the source mounted, but no test/lint executions yet.
    # The lint-only and test-only functions below compose on top of them so
    # Dagger's content-addressed cache reuses the apt/uv/npm steps across
    # phases. That's what makes the lint-then-test split fast on second pass.

    def _api_base(self, src: dagger.Directory) -> dagger.Container:
        src = (
            src
            .without_directory(".venv")
            .without_directory("staticfiles")
            .without_directory(".git")
        )
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
            .with_directory("/app", src)
            .with_exec(["uv", "sync", "--frozen"])
        )

    def _frontend_base(self, src: dagger.Directory) -> dagger.Container:
        src = (
            src
            .without_directory("node_modules")
            .without_directory("dist")
            .without_directory(".git")
        )
        # Firefox in `node:20-slim` fails with
        # "RenderCompositorSWGL failed mapping default framebuffer"
        # under `-headless` because there's no /dev/dri. xvfb-run gives
        # firefox a virtual framebuffer; xauth is needed for the cookie.
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
            .with_directory("/app", src)
        )

    # ── Lint-only (cheap, fail-fast) ───────────────────────────────────────

    @function
    async def lint_api(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../api")],
    ) -> dagger.Container:
        """Ruff + bandit on the api source. No db, no test suite."""
        return (
            self._api_base(src)
            .with_exec(["uv", "run", "ruff", "check", "."])
            .with_exec(["uv", "run", "bandit", "-r", ".", "-x", "*/migrations/*,./.venv/*", "-ll"])
        )

    @function
    async def lint_frontend(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../frontend")],
    ) -> dagger.Container:
        """eslint + prettier + ember-template-lint + stylelint. No tests."""
        return self._frontend_base(src).with_exec(["npm", "run", "lint"])

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
            self._api_base(src)
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
                "uv run python manage.py test -v 2 --keepdb --noinput 2>&1 "
                "| tee /test.log",
            ])
            # Belt-and-suspenders: even if the runner ever exits 0 with
            # zero tests collected or swallowed failures, require the
            # canonical success markers in the log. Tally #9/#13/#14/#19 —
            # this assertion closes the green-but-broken gap.
            .with_exec([
                "sh", "-c",
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
            self._frontend_base(src)
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
            .with_exec([
                "sh", "-c",
                "grep -qE '^# fail +0$' /tap.log "
                "&& grep -qE '^# pass +[1-9]' /tap.log",
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
            self._api_base(src)
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
                "uv run python manage.py test -v 2 --keepdb --noinput 2>&1 "
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
            self._frontend_base(src)
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
            .with_exec(["uv", "sync", "--frozen", "--no-install-project"])
            .with_directory("/app", src)
            .with_exec(["uv", "sync", "--frozen"])
            .with_env_variable("LOGFIRE_SEND_TO_LOGFIRE", "false")
            .with_exec(["uv", "run", "pytest", "tests/", "-v"])
        )

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
    ) -> list[str]:
        """Build all images and push to GHCR. Returns list of pushed image refs.

        Args:
            registry_token: GitHub token with packages:write permission
            org: GitHub organization (used in image path)
            tag: Image tag (use git SHA for immutable tags)
            registry_username: GitHub actor username for GHCR auth (defaults to org)
        """
        username = registry_username or org
        api_ref = f"{REGISTRY}/{org}/{API_IMAGE}:{tag}"
        frontend_ref = f"{REGISTRY}/{org}/{FRONTEND_IMAGE}:{tag}"
        ai_ref = f"{REGISTRY}/{org}/{AI_IMAGE}:{tag}"

        pushed_api = await (
            api_src
            .docker_build()
            .with_registry_auth(REGISTRY, username, registry_token)
            .publish(api_ref)
        )

        pushed_frontend = await (
            frontend_src
            .docker_build()
            .with_registry_auth(REGISTRY, username, registry_token)
            .publish(frontend_ref)
        )

        # AI image: build without Camoufox (browser runs on Pi, not VPS)
        pushed_ai = await (
            ai_src
            .docker_build(build_args=[dagger.BuildArg("INSTALL_CAMOUFOX", "false")])
            .with_registry_auth(REGISTRY, username, registry_token)
            .publish(ai_ref)
        )

        return [pushed_api, pushed_frontend, pushed_ai]

    @function
    async def deploy(
        self,
        ssh_key: Secret,
        host: str,
        compose_file: Annotated[dagger.File, DefaultPath("../docker-compose.prod.yml")],
        app_dir: str = "/home/oldbones/Projects/career_caddy",
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
                    f"docker image prune -f",
                ]
            )
            .stdout()
        )
