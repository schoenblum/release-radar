#!/bin/sh
# End-to-end tests (step 1.9): the production image against a throwaway database, driven by
# Playwright in its own container. Nothing is installed on the host and nothing is left behind.
#   sh scripts/e2e.sh                  run them
#   E2E_KEEP=1 sh scripts/e2e.sh       keep the stack afterwards, at http://localhost:8098
#   sh scripts/e2e.sh --grep paste     pass options to Playwright
set -eu
cd "$(dirname "$0")/../e2e"

compose() { docker compose -f compose.yaml "$@"; }
finish() {
  if [ "${E2E_KEEP:-}" = "1" ]; then
    echo "The stack is still up at http://localhost:${E2E_PORT:-8098}. Stop it with:"
    echo "  docker compose -f e2e/compose.yaml down -v"
  else
    compose down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap finish EXIT

compose down -v --remove-orphans >/dev/null 2>&1 || true
compose build app
compose up -d --wait db crossref app
status=0
if [ "$#" -gt 0 ]; then
  compose run --rm tests sh -c "npm ci --no-audit --no-fund && npx tsc --noEmit && npx playwright test $*" || status=$?
else
  compose run --rm tests || status=$?
fi
if [ "$status" -ne 0 ]; then
  echo "== The app's last log lines"
  compose logs --tail 60 app
  echo "The report is in e2e/playwright-report (open index.html)."
fi
exit "$status"
