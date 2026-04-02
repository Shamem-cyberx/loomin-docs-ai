#!/usr/bin/env python3
"""
Test RAG against the library (e.g. Luna PDF).

  Fast (default, seconds): POST /api/rag/search only — no LLM. Proves retrieval finds the right text.

  With LLM (minutes on CPU): --llm runs one short /api/chat call.

  WSL:
    python3 /mnt/e/loomin-docs/scripts/verify_luna_accuracy.py
    python3 /mnt/e/loomin-docs/scripts/verify_luna_accuracy.py --llm
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("LOOMIN_BASE", "http://127.0.0.1:8000")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT_S", "1900"))


def post_json(base: str, path: str, body: dict, timeout: int) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def req(base: str, path: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(f"{base}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode())


def fast_mode(base: str) -> int:
    print("=== Fast retrieval test (no LLM) ===")
    print("GET", base + "/api/rag/status")
    st = req(base, "/api/rag/status")
    print(json.dumps(st, indent=2))
    if st.get("meta_rows", 0) <= 0:
        print("FAIL: no vectors in index — upload a PDF first.", file=sys.stderr)
        return 1

    cases: list[tuple[str, list[str]]] = [
        ("Who is Luna and what does she do?", ["luna", "dream"]),
        ("Emma girl Mr Whiskers bedroom", ["emma"]),
        ("Stardust unicorn Whisper owl Shimmer phoenix", ["stardust", "whisper", "shimmer"]),
    ]

    all_ok = True
    for i, (question, keys) in enumerate(cases, 1):
        print(f"\n--- Query {i}: {question!r} ---")
        t0 = time.perf_counter()
        try:
            out = post_json(base, "/api/rag/search", {"query": question, "top_k": 4}, timeout=120)
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, e.read().decode()[:600], file=sys.stderr)
            return 1
        wall = time.perf_counter() - t0
        print(f"retrieval_time_ms={out['retrieval_time_ms']} wall_s={wall:.2f}")
        chunks = out.get("chunks") or []
        if not chunks:
            print("FAIL: no chunks returned", file=sys.stderr)
            all_ok = False
            continue
        blob = "\n".join(c["text"] for c in chunks).lower()
        missing = [k for k in keys if k not in blob]
        if missing:
            print("WEAK: expected keywords not in top chunks:", missing)
            print("First chunk preview:", (chunks[0].get("text") or "")[:400], "…")
            all_ok = False
        else:
            print("OK: keywords found in retrieved chunks:", keys)
        print("Top chunk:", chunks[0].get("file"), chunks[0].get("chunk_id"))

    if all_ok:
        print("\nPASS — retrieval matches Luna story content (fast path).")
    else:
        print("\nINCOMPLETE — tune RAG or re-ingest; LLM answers still depend on retrieval.", file=sys.stderr)
    return 0 if all_ok else 1


def llm_mode(base: str) -> int:
    print("\n=== One LLM RAG call (slow on CPU; first load can take several minutes) ===")
    sid = post_json(base, "/api/chat/sessions", {}, timeout=60)["id"]
    msg = "In one sentence: who is Luna and who is Emma in the uploaded story?"
    t0 = time.perf_counter()
    try:
        out = post_json(
            base,
            "/api/chat",
            {
                "message": msg,
                "session_id": sid,
                "use_rag": True,
                "model": os.environ.get("OLLAMA_MODEL", "qwen2.5:0.5b"),
            },
            timeout=LLM_TIMEOUT,
        )
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:800], file=sys.stderr)
        return 1
    wall = time.perf_counter() - t0
    print("Q:", msg)
    print("A:", (out.get("answer") or "").strip())
    print(
        "metrics:",
        "retrieval_ms=",
        out.get("retrieval_time_ms"),
        "llm_ms=",
        out.get("llm_latency_ms"),
        "wall_s=%.1f" % wall,
        "tps=",
        out.get("generation_speed_tps"),
    )
    ans = (out.get("answer") or "").lower()
    if "luna" in ans and "emma" in ans:
        print("PASS — answer mentions Luna and Emma.")
        return 0
    print("CHECK MANUALLY — expected names Luna and Emma in answer.", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--llm", action="store_true", help="also run one slow LLM chat")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    try:
        req(base, "/health", timeout=10)
    except Exception as e:
        print("FAIL: API not reachable at", base, e, file=sys.stderr)
        return 1

    rc = fast_mode(base)
    if args.llm:
        rc2 = llm_mode(base)
        rc = rc or rc2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
