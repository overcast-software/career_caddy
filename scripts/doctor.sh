#!/usr/bin/env bash
# scripts/doctor.sh — Career Caddy environment diagnostics
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
CHECK_POLLER=false

for arg in "$@"; do
  case "$arg" in
    --poller) CHECK_POLLER=true ;;
    --no-color) NO_COLOR=1 ;;
  esac
done

# ── Colors ────────────────────────────────────────────────────────────────
if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
  GREEN="\033[32m"
  YELLOW="\033[33m"
  RED="\033[31m"
  BOLD="\033[1m"
  DIM="\033[2m"
  RESET="\033[0m"
else
  GREEN="" YELLOW="" RED="" BOLD="" DIM="" RESET=""
fi

pass()  { PASS_COUNT=$((PASS_COUNT + 1)); echo -e "  ${GREEN}✓${RESET} $1"; }
warn()  { WARN_COUNT=$((WARN_COUNT + 1)); echo -e "  ${YELLOW}⚠${RESET} $1"; }
fail()  { FAIL_COUNT=$((FAIL_COUNT + 1)); echo -e "  ${RED}✗${RESET} $1"; }
header(){ echo -e "\n${BOLD}$1${RESET}"; }

# ── Helper: read a value from .env ────────────────────────────────────────
env_val() {
  grep -E "^${1}=" "$PROJECT_ROOT/.env" 2>/dev/null | head -1 | cut -d'=' -f2-
}

env_set() {
  local val
  val="$(env_val "$1")"
  [[ -n "$val" ]]
}

# ── Helper: check if a port is in use ────────────────────────────────────
port_in_use() {
  if command -v ss &>/dev/null; then
    ss -tlnp 2>/dev/null | grep -q ":${1} "
  elif command -v lsof &>/dev/null; then
    lsof -iTCP:"$1" -sTCP:LISTEN &>/dev/null
  else
    (echo >/dev/tcp/127.0.0.1/"$1") 2>/dev/null
  fi
}

echo -e "${BOLD}Career Caddy Doctor${RESET}"
echo "==================="

# ── Group 1: Core Environment ─────────────────────────────────────────────
header "Core Environment"

if docker info &>/dev/null; then
  pass "Docker daemon is running"
else
  fail "Docker daemon is not running"
fi

if docker compose version &>/dev/null; then
  ver=$(docker compose version --short 2>/dev/null || echo "unknown")
  pass "Docker Compose v2 available ($ver)"
else
  fail "Docker Compose v2 not found — install docker-compose-plugin"
fi

if command -v make &>/dev/null; then
  pass "Make is available"
else
  fail "Make is not installed"
fi

if [[ -f "$PROJECT_ROOT/.env" ]]; then
  pass ".env file exists"
else
  fail ".env file missing — run: cp .env.example .env"
fi

# ── Group 2: Environment Variables ────────────────────────────────────────
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  header "Environment Variables"

  if env_set OPENAI_API_KEY || env_set ANTHROPIC_API_KEY; then
    pass "AI API key is set (OpenAI or Anthropic)"
  else
    fail "No AI API key — set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env"
  fi

  if env_set DB_PASSWORD; then
    pass "DB_PASSWORD is set"
  else
    fail "DB_PASSWORD is not set in .env"
  fi

  secret_key="$(env_val SECRET_KEY)"
  if [[ "$secret_key" == "replace-with-a-secure-random-value" ]] || [[ -z "$secret_key" ]]; then
    warn "SECRET_KEY is using the placeholder — generate a real value for production"
  else
    pass "SECRET_KEY is configured"
  fi
fi

# ── Group 3: Ports ────────────────────────────────────────────────────────
header "Ports"

for port in 4200 8000 5432; do
  if port_in_use "$port"; then
    # Check if it's a Career Caddy container
    if docker compose -f "$PROJECT_ROOT/docker-compose.yml" ps --format json 2>/dev/null | grep -q "running"; then
      pass "Port $port in use (Career Caddy stack is running)"
    else
      warn "Port $port is already in use (may conflict with make up)"
    fi
  else
    pass "Port $port is free"
  fi
done

# ── Group 4: Docker Services ─────────────────────────────────────────────
running_containers=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" ps --format json 2>/dev/null | head -1)
if [[ -n "$running_containers" ]]; then
  header "Docker Services"

  for svc in db api frontend chat browser-mcp; do
    status=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" ps --status running --format "{{.Name}}" 2>/dev/null | grep -c "$svc" || true)
    if [[ "$status" -gt 0 ]]; then
      health=$(docker compose -f "$PROJECT_ROOT/docker-compose.yml" ps --format json 2>/dev/null | grep "$svc" | grep -o '"Health":"[^"]*"' | cut -d'"' -f4 || true)
      if [[ "$health" == "healthy" ]]; then
        pass "$svc: healthy"
      else
        pass "$svc: running"
      fi
    else
      echo -e "  ${DIM}— $svc: not running${RESET}"
    fi
  done
else
  header "Docker Services"
  echo -e "  ${DIM}No containers running — start with: make up${RESET}"
fi

# ── Group 5: Hold-Poller ─────────────────────────────────────────────────
if $CHECK_POLLER || env_set CC_API_TOKEN 2>/dev/null; then
  header "Hold-Poller"

  if command -v uv &>/dev/null; then
    uv_ver=$(uv --version 2>/dev/null || echo "unknown")
    pass "uv is installed ($uv_ver)"
  else
    fail "uv is not installed — see https://docs.astral.sh/uv/"
  fi

  if [[ -d "$PROJECT_ROOT/agents" ]]; then
    if (cd "$PROJECT_ROOT/agents" && uv run python -c "import camoufox" 2>/dev/null); then
      pass "Camoufox is importable"
    else
      fail "Camoufox not available — run: cd agents && uv sync && python -m camoufox fetch"
    fi
  fi

  if env_set CC_API_TOKEN; then
    pass "CC_API_TOKEN is set"
  else
    fail "CC_API_TOKEN not set — create one at /admin/api-keys"
  fi

  api_url="$(env_val CC_API_BASE_URL)"
  if [[ -n "$api_url" ]]; then
    pass "CC_API_BASE_URL is set ($api_url)"
    if curl -fsS --max-time 5 "${api_url}/api/v1/healthcheck/" &>/dev/null; then
      pass "API is reachable at $api_url"
    else
      warn "API not reachable at $api_url (is the stack running?)"
    fi
  else
    fail "CC_API_BASE_URL not set in .env"
  fi
fi

# ── Group 6: Browser Automation ──────────────────────────────────────────
if [[ -d "$PROJECT_ROOT/agents" ]]; then
  header "Browser Automation"

  if [[ -f "$PROJECT_ROOT/agents/secrets.yml" ]]; then
    pass "agents/secrets.yml exists"
  else
    warn "agents/secrets.yml missing — needed for login automation (cp agents/secrets.yml.example agents/secrets.yml)"
  fi
fi

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo "─────────────"
total=$((PASS_COUNT + WARN_COUNT + FAIL_COUNT))
echo -e "Results: ${GREEN}${PASS_COUNT} passed${RESET}, ${YELLOW}${WARN_COUNT} warnings${RESET}, ${RED}${FAIL_COUNT} failed${RESET} (${total} checks)"

if [[ $FAIL_COUNT -gt 0 ]]; then
  exit 1
fi
