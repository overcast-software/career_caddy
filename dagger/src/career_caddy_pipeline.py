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
      Defaults: ../api → api/, ../frontend → frontend/, ../ai → ai/
      Override: --src=./path/to/dir (or --api-src=, --frontend-src=, etc.)
"""

from __future__ import annotations

from typing import Annotated

import dagger
from dagger import DefaultPath, dag, function, object_type, Secret


REGISTRY = "ghcr.io"
API_IMAGE = "career_caddy_api"
FRONTEND_IMAGE = "career-caddy-frontend"


@object_type
class CareerCaddy:

    @function
    async def build_api(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../api")],
    ) -> dagger.Container:
        """Build the Django API image and run linting + tests.

        Runs: ruff check, bandit security scan, Django test suite.
        Requires a PostgreSQL service (started automatically as a sidecar).
        """
        src = (
            src
            .without_directory(".venv")
            .without_directory("staticfiles")
            .without_directory(".git")
        )

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
            .with_directory("/app", src)
            .with_workdir("/app")
            .with_exec(["uv", "sync", "--frozen"])
            .with_service_binding("db", pg)
            .with_env_variable(
                "DATABASE_URL", "postgresql://postgres:postgres@db:5432/job_hunting_ci"
            )
            .with_env_variable("SECRET_KEY", "ci-test-secret-not-for-production")
            .with_env_variable("DEBUG", "True")
            .with_exec(["uv", "run", "ruff", "check", "."])
            .with_exec(["uv", "run", "bandit", "-r", ".", "-x", "*/migrations/*,./.venv/*", "-ll"])
            .with_exec(["uv", "run", "python", "manage.py", "test", "-v", "2"])
        )

    @function
    async def build_frontend(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../frontend")],
    ) -> dagger.Container:
        """Build the Ember.js frontend image and run lint + tests."""
        src = (
            src
            .without_directory("node_modules")
            .without_directory("dist")
            .without_directory(".git")
        )

        return (
            dag.container()
            .from_("node:20-slim")
            .with_exec(
                [
                    "sh", "-c",
                    "apt-get update && apt-get install -y --no-install-recommends "
                    "chromium && rm -rf /var/lib/apt/lists/*",
                ]
            )
            .with_directory("/app", src)
            .with_workdir("/app")
            .with_env_variable("CI", "true")
            .with_exec(["npm", "ci"])
            .with_exec(["npm", "run", "lint"])
            .with_exec(["npm", "run", "test:ember"])
        )

    @function
    async def build_ai(
        self,
        src: Annotated[dagger.Directory, DefaultPath("../ai")],
    ) -> dagger.Container:
        """Build the slim AI agent image (Python 3.13, no Camoufox — production image).

        Camoufox (~700 MB) is excluded from the production image. The browser-mcp
        service is only for local dev and is built separately via docker compose
        with INSTALL_CAMOUFOX=true.
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
            .with_directory("/app", src)
            .with_workdir("/app")
            .with_exec(["uv", "sync", "--frozen", "--no-dev"])
        )

    @function
    async def publish(
        self,
        registry_token: Secret,
        api_src: Annotated[dagger.Directory, DefaultPath("../api")],
        frontend_src: Annotated[dagger.Directory, DefaultPath("../frontend")],
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

        return [pushed_api, pushed_frontend]

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
            .with_exec(["sh", "-c", "mkdir -p /root/.ssh && chmod 700 /root/.ssh && tr -d '\\r' < /run/secrets/ssh_key > /root/.ssh/id_ed25519 && chmod 600 /root/.ssh/id_ed25519"])
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
