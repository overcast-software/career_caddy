"""
Career Caddy — Dagger CI/CD Pipeline

Replaces the scattered GitHub Actions YAML across api/ and frontend/.
Run the same build/test/deploy pipeline locally and in CI.

Usage (from repo root):
  dagger -m ./dagger call build-api
  dagger -m ./dagger call build-frontend
  dagger -m ./dagger call build-ai
  dagger -m ./dagger call publish --registry-token=env:GITHUB_TOKEN --org=overcast-software --tag=latest
  dagger -m ./dagger call deploy --ssh-key=file:~/.ssh/id_ed25519 --host=your-vps-ip --app-dir=/opt/career-caddy --tag=latest

In GitHub Actions, call via: dagger -m ./dagger call publish ...
"""

from __future__ import annotations

import dagger
from dagger import dag, function, object_type, Secret


REGISTRY = "ghcr.io"
API_IMAGE = "career_caddy_api"
FRONTEND_IMAGE = "career-caddy-frontend"


@object_type
class CareerCaddy:

    @function
    async def build_api(self) -> dagger.Container:
        """Build the Django API image and run linting + tests.

        Runs: ruff check, bandit security scan, Django test suite.
        Requires a PostgreSQL service (started automatically as a sidecar).
        """
        src = dag.host().directory(
            "./api",
            exclude=[".venv", "__pycache__", "*.pyc", ".git", "staticfiles"],
        )

        pg = (
            dag.container()
            .from_("postgres:18")
            .with_env_variable("POSTGRES_DB", "job_hunting_ci")
            .with_env_variable("POSTGRES_USER", "postgres")
            .with_env_variable("POSTGRES_PASSWORD", "postgres")
            .with_exposed_port(5432)
            .as_service(name="db")
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
            .with_env_variable(
                "SECRET_KEY", "ci-test-secret-not-for-production"
            )
            .with_env_variable("DEBUG", "True")
            # Lint
            .with_exec(["uv", "run", "ruff", "check", "."])
            .with_exec(
                ["uv", "run", "bandit", "-r", ".", "-x", "*/migrations/*", "-ll"]
            )
            # Tests (hit real DB, matching api/CLAUDE.md guidance)
            .with_exec(
                ["uv", "run", "python", "manage.py", "test", "-v", "2"]
            )
        )

    @function
    async def build_frontend(self) -> dagger.Container:
        """Build the Ember.js frontend image and run lint + tests."""
        src = dag.host().directory(
            "./frontend",
            exclude=["node_modules", "dist", ".pnpm-store", ".git"],
        )

        return (
            dag.container()
            .from_("node:20-slim")
            .with_directory("/app", src)
            .with_workdir("/app")
            .with_exec(["npm", "ci"])
            .with_exec(["npm", "run", "lint"])
            .with_exec(["npm", "run", "test:ember"])
        )

    @function
    async def build_ai(self) -> dagger.Container:
        """Build the AI agent image (Python 3.13 + Camoufox browser binary)."""
        src = dag.host().directory(
            "./ai",
            exclude=[
                ".venv",
                "__pycache__",
                "*.pyc",
                ".git",
                "screenshots",
                "secrets.yml",
            ],
        )

        return (
            dag.container()
            .from_("python:3.13-slim")
            .with_exec(
                [
                    "sh", "-c",
                    "apt-get update && apt-get install -y --no-install-recommends "
                    "build-essential curl libglib2.0-0 libnss3 libatk1.0-0 "
                    "libgbm1 libasound2 && rm -rf /var/lib/apt/lists/*",
                ]
            )
            .with_exec(["pip", "install", "uv"])
            .with_directory("/app", src)
            .with_workdir("/app")
            .with_exec(["uv", "sync", "--frozen", "--no-dev"])
            .with_env_variable("CAMOUFOX_DATA_DIR", "/opt/camoufox")
            .with_exec(["uv", "run", "python", "-m", "camoufox", "fetch"])
        )

    @function
    async def publish(
        self,
        registry_token: Secret,
        org: str = "overcast-software",
        tag: str = "latest",
    ) -> list[str]:
        """Build all images and push to GHCR. Returns list of pushed image refs.

        Args:
            registry_token: GitHub token with packages:write permission
            org: GitHub organization / username
            tag: Image tag (use git SHA for immutable tags)
        """
        api_ref = f"{REGISTRY}/{org}/{API_IMAGE}:{tag}"
        frontend_ref = f"{REGISTRY}/{org}/{FRONTEND_IMAGE}:{tag}"

        api_src = dag.host().directory(
            "./api",
            exclude=[".venv", "__pycache__", "*.pyc", ".git", "staticfiles"],
        )
        frontend_src = dag.host().directory(
            "./frontend",
            exclude=["node_modules", "dist", ".pnpm-store", ".git"],
        )

        pushed_api = await (
            api_src
            .docker_build()
            .with_registry_auth(REGISTRY, org, registry_token)
            .publish(api_ref)
        )

        pushed_frontend = await (
            frontend_src
            .docker_build()
            .with_registry_auth(REGISTRY, org, registry_token)
            .publish(frontend_ref)
        )

        return [pushed_api, pushed_frontend]

    @function
    async def deploy(
        self,
        ssh_key: Secret,
        host: str,
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
        compose_file = dag.host().file("./docker-compose.prod.yml")

        return await (
            dag.container()
            .from_("alpine:3.19")
            .with_exec(["apk", "add", "--no-cache", "openssh-client", "docker-cli"])
            .with_mounted_secret("/root/.ssh/id_rsa", ssh_key)
            .with_exec(["chmod", "600", "/root/.ssh/id_rsa"])
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
                    "-i",
                    "/root/.ssh/id_rsa",
                    "/workspace/docker-compose.prod.yml",
                    f"{ssh_user}@{host}:{app_dir}/docker-compose.prod.yml",
                ]
            )
            .with_exec(
                [
                    "ssh",
                    "-i",
                    "/root/.ssh/id_rsa",
                    f"{ssh_user}@{host}",
                    f"cd {app_dir} && "
                    f"sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG={tag}/' .env || echo 'IMAGE_TAG={tag}' >> .env && "
                    f"docker compose -f docker-compose.prod.yml pull && "
                    f"docker compose -f docker-compose.prod.yml up -d --remove-orphans && "
                    f"docker image prune -f",
                ]
            )
            .stdout()
        )
