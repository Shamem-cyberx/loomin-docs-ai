#!/usr/bin/env bash
# Run all checks aligned with project-assesment.md; log everything to assessment-run.log
# Usage (from repo root in WSL):
#   chmod +x scripts/run_assessment_verification.sh
#   ./scripts/run_assessment_verification.sh
#
# Prerequisites: Docker (compose v2 or v1), curl, python3 (stdlib only for HTTP scripts).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG="$ROOT/assessment-run.log"
COMPOSE=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
fi

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

exec > >(tee -a "$LOG") 2>&1

echo "=============================================="
echo "Loomin-Docs assessment verification"
echo "Started: $(date -Iseconds)"
echo "Repo: $ROOT"
echo "Log: $LOG"
echo "=============================================="

section() {
  echo ""
  echo "######## $* ########"
}

section "0) Docker"
command -v docker
docker --version
"${COMPOSE[@]}" version || true

section "1) Stack up (build --parallel if images missing; use COMPOSE_PROFILES=bundle for container Ollama)"
"${COMPOSE[@]}" build --parallel
"${COMPOSE[@]}" up -d

section "2) Wait for API (http://127.0.0.1:8000/health)"
ok=0
for i in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" != "1" ]]; then
  echo "FAIL: API not healthy. Try: ${COMPOSE[*]} logs backend"
  exit 1
fi
curl -sS http://127.0.0.1:8000/health
echo

section "3) Ingest sample PDFs (Luna + Kai) for live RAG scripts"
upload() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  echo "--- upload $(basename "$f") ---"
  curl -sS -X POST -F "upload=@${f}" http://127.0.0.1:8000/api/files/upload | python3 -m json.tool || true
  echo
}
upload "$ROOT/Luna_the_Dream_Keeper.pdf"
upload "$ROOT/Kai_and_the_Guardian_Realm.pdf"

section "4) Retrieval scripts (faithfulness of RETRIEVAL vs corpus)"
echo "--- multi_query_rag_test.py ---"
python3 "$ROOT/scripts/multi_query_rag_test.py"; mq=$?
echo "exit_code=$mq"

echo "--- targeted_rag_checks.py ---"
python3 "$ROOT/scripts/targeted_rag_checks.py"; tg=$?
echo "exit_code=$tg"

echo "--- complex_rag_tests.py ---"
python3 "$ROOT/scripts/complex_rag_tests.py"; cx=$?
echo "exit_code=$cx"

section "5) test_rag.py (assessment: RAG faithfulness smoke test)"
# Run inside backend image so deps match production; no Ollama required with SKIP_OLLAMA=1
"${COMPOSE[@]}" run --rm --no-deps \
  -v "$ROOT:/repo:ro" \
  -w /repo \
  -e DATA_DIR=/tmp/loomin_rag_verify \
  -e SKIP_OLLAMA=1 \
  backend \
  python test_rag.py; tr=$?
echo "test_rag.py exit_code=$tr"

section "6) Assessment crosswalk (what passed)"
echo "multi_query_rag_test.py     => exit $mq  (0=PASS heuristic substring checks)"
echo "targeted_rag_checks.py      => exit $tg"
echo "complex_rag_tests.py        => exit $cx"
echo "test_rag.py (SKIP_OLLAMA=1) => exit $tr  (0=PASS retrieval + fixture facts)"
overall=0
for x in "$mq" "$tg" "$cx" "$tr"; do
  if [[ "$x" != "0" ]]; then overall=1; fi
done
echo "OVERALL_EXIT=$overall  (0 if all four scripts exited 0)"
echo "Finished: $(date -Iseconds)"
echo "Full log: $LOG"

exit "$overall"
