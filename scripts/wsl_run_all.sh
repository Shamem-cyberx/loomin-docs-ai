#!/usr/bin/env bash
# One command: start stack (optional build), wait for API, upload sample PDFs if empty, run RAG test scripts.
#
# Default repo path under WSL (change if your clone lives elsewhere):
#   export LOOMIN_ROOT=/mnt/c/Users/YourName/loomin-docs
#   bash scripts/wsl_run_all.sh
#
# Options (env):
#   SKIP_BUILD=1       â€” docker compose up -d only (no --build)
#   SKIP_UPLOAD=1      â€” do not POST Luna/Kai PDFs (use if already indexed)
#   COMPOSE="docker compose" â€” override if you use v1 docker-compose
set -euo pipefail

LOOMIN_ROOT="${LOOMIN_ROOT:-/mnt/e/loomin-docs}"
cd "$LOOMIN_ROOT" || {
  echo "ERROR: LOOMIN_ROOT not found: $LOOMIN_ROOT"
  echo "Find your Windows path (e.g. E:\\loomin-docs) and set:"
  echo "  export LOOMIN_ROOT=/mnt/e/loomin-docs"
  exit 1
}

COMPOSE="${COMPOSE:-docker compose}"
if ! $COMPOSE version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

echo "=== loomin-docs: repo=$LOOMIN_ROOT compose=$COMPOSE ==="
echo "=== Tip: .env with host Ollama + no COMPOSE_PROFILES skips bundled ollama (faster pull) ==="

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not in PATH. Install Docker Desktop and enable WSL integration, or use Linux with Docker."
  exit 1
fi

BASE="${BASE:-http://127.0.0.1:8000}"

if [[ "${SKIP_BUILD:-}" == "1" ]]; then
  echo "=== docker compose up -d (no build) ==="
  $COMPOSE up -d
else
  echo "=== docker compose build --parallel && up -d (BuildKit caches pip/npm) ==="
  $COMPOSE build --parallel
  $COMPOSE up -d
fi

echo "=== wait for $BASE/health (max 180s) ==="
ok=0
for i in $(seq 1 90); do
  if curl -sf "$BASE/health" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" != "1" ]]; then
  echo "ERROR: API did not become healthy. Try: $COMPOSE logs backend"
  exit 1
fi
curl -sS "$BASE/health"
echo

upload_pdf() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  echo "=== upload $(basename "$f") ==="
  curl -sS -X POST -F "upload=@${f}" "$BASE/api/files/upload" | python3 -m json.tool || true
  echo
}

if [[ "${SKIP_UPLOAD:-}" != "1" ]]; then
  upload_pdf "$LOOMIN_ROOT/Luna_the_Dream_Keeper.pdf"
  upload_pdf "$LOOMIN_ROOT/Kai_and_the_Guardian_Realm.pdf"
fi

run_py() {
  local name="$1"
  shift
  echo ""
  echo "######################################################################"
  echo "### $name"
  echo "######################################################################"
  python3 "$@" || return 1
}

ec=0
run_py "multi_query_rag_test.py" "$LOOMIN_ROOT/scripts/multi_query_rag_test.py" || ec=1
run_py "targeted_rag_checks.py" "$LOOMIN_ROOT/scripts/targeted_rag_checks.py" || ec=1
run_py "complex_rag_tests.py" "$LOOMIN_ROOT/scripts/complex_rag_tests.py" || ec=1

echo ""
echo "=== done (exit $ec) â€” retrieval scripts finished ==="
exit "$ec"
