#!/bin/sh
# Run every check CI runs, inside the containers. Run this before pushing.
set -eu
cd "$(dirname "$0")/.."

backend() { docker compose --profile dev run --rm app-dev "$@"; }
frontend() { docker compose --profile dev run --rm --no-deps frontend sh -c "$1"; }

echo "== Compose files"
docker compose --profile dev --profile prod --profile proxy config --quiet

echo "== i18n parity"
backend python scripts/check_i18n.py

echo "== Python lint"
backend ruff check .
backend ruff format --check .

echo "== Python tests"
backend pytest

echo "== Frontend lint, types, tests, build"
frontend "npm ci --no-audit --no-fund && npm run lint && npm run typecheck && npm test && npm run build"

echo "All checks passed."
