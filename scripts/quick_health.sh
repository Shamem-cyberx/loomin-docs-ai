#!/usr/bin/env bash
# Fast stack check — no LLM call (seconds, not minutes).
# WSL: bash scripts/quick_health.sh   OR   wsl -u root bash /mnt/e/loomin-docs/scripts/quick_health.sh
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"
echo "GET $BASE/health"
curl -sS "$BASE/health"
echo
echo "GET $BASE/api/ready"
curl -sS "$BASE/api/ready"
echo
