#!/usr/bin/env bash
# Single runner for the LAN Mouse & Keyboard test suite. Same commands the CI runs.
#
#   ./run-tests.sh            -> lint + backend (pytest, fake uinput) + frontend unit (node)
#   RUN_E2E=1 ./run-tests.sh  -> also the Playwright E2E (needs tests/frontend/node_modules)
#
# Never opens /dev/uinput and never starts the real server: nothing moves the PC's mouse.
set -u
cd "$(dirname "$0")" || exit

PY="${PY:-venv/bin/python}"
[ -x "$PY" ] || PY=".venv/bin/python"
FAILED=0
declare -a RESULTS

bar() { printf '%s\n' "------------------------------------------------------------"; }
run_layer() {  # run_layer <name> <command...>
  local name="$1"; shift
  bar; echo ">> $name"; bar
  if "$@"; then RESULTS+=("PASS  $name"); else RESULTS+=("FAIL  $name"); FAILED=1; fi
}

# ---------- lint (ruff from the venv; shellcheck when installed) ----------
run_layer "lint     (ruff)" "$PY" -m ruff check .
if command -v shellcheck > /dev/null; then
  run_layer "lint     (shellcheck)" shellcheck --severity=warning ./*.sh
else
  RESULTS+=("SKIP  lint (shellcheck) - sudo apt install shellcheck")
fi

# ---------- backend (pytest, fake uinput, TestClient) ----------
run_layer "backend  (pytest)" "$PY" -m pytest -q

# ---------- frontend unit (node:test, i18n catalog) ----------
run_layer "frontend (node:test i18n)" node --test 'tests/frontend/*.test.mjs'

# ---------- E2E (opt-in) ----------
if [ "${RUN_E2E:-0}" = "1" ]; then
  run_layer "e2e      (Playwright, fake WebSocket)" bash -c 'cd tests/frontend && npx playwright test --reporter=line'
else
  RESULTS+=("SKIP  e2e (Playwright) - RUN_E2E=1 to run it")
fi

# ---------- scoreboard ----------
echo ""; bar; echo "SCOREBOARD"; bar
for r in "${RESULTS[@]}"; do echo "  $r"; done
bar
if [ "$FAILED" -eq 0 ]; then echo "ALL GREEN ✅"; else echo "FAILURES ❌"; fi
exit "$FAILED"
