#!/usr/bin/env bash
# Timed RAG calls (WSL: wsl -u root bash /mnt/e/loomin-docs/scripts/bench_rag.sh)
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8000}"
PDF="${1:-/mnt/e/loomin-docs/Luna_the_Dream_Keeper.pdf}"

echo "=== health ==="
curl -sS "$BASE/health"
echo

echo "=== session ==="
SID=$(curl -sS -X POST "$BASE/api/chat/sessions" -H 'Content-Type: application/json' -d '{}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
echo "session=$SID"

if [[ "${SKIP_UPLOAD:-}" == "1" ]]; then
  echo "=== skip upload (SKIP_UPLOAD=1) ==="
elif [[ -f "$PDF" ]]; then
  echo "=== upload (ingest) ==="
  curl -sS -X POST -F "upload=@${PDF}" "$BASE/api/files/upload" | python3 -m json.tool
else
  echo "skip upload (no file $PDF)"
fi

export BASE SID
python3 <<'PY'
import json, os, time, urllib.request

base = os.environ["BASE"]
sid = os.environ["SID"]
msg = "Who is Luna and what is her role? Answer in 2 short sentences using only the document."

for n in (1, 2):
    body = json.dumps({
        "message": msg if n == 1 else "Again: one sentence — who is Luna?",
        "session_id": sid,
        "use_rag": True,
        "model": "llama3:latest",
    }).encode()
    req = urllib.request.Request(
        f"{base}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1900) as r:
        raw = r.read().decode()
    wall = time.perf_counter() - t0
    d = json.loads(raw)
    print(f"\n=== RAG chat #{n} wall={wall:.2f}s ===")
    print("answer:", (d.get("answer") or "")[:500])
    print("retrieval_ms:", d.get("retrieval_time_ms"))
    print("llm_latency_ms:", d.get("llm_latency_ms"))
    print("generation_speed_tps:", d.get("generation_speed_tps"))
PY
