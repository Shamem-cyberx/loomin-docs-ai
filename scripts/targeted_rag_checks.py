#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.request

BASE = "http://127.0.0.1:8000"

QUERIES = [
    # Luna
    ("Sweet Dreams Publishing illustrated by", ["sweet dreams", "publishing"]),
    ("Where does Emma live? cozy cottage edge of an enchanted forest", ["cottage", "enchanted forest"]),
    ("What color are Emma's eyes?", ["blue eyes"]),
    # Kai
    ("What object did Kai find in the attic?", ["leather journal"]),
    ("What color are Kai's eyes?", ["green", "eyes"]),
    ("Who is Theron and what is his title?", ["guardian of stories"]),
]


def rag_search(q: str, top_k: int = 6) -> dict:
    body = json.dumps({"query": q, "top_k": top_k}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/rag/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    with urllib.request.urlopen(f"{BASE}/health", timeout=15) as r:
        print("health:", r.read().decode())

    all_ok = True
    for q, needles in QUERIES:
        t0 = time.perf_counter()
        out = rag_search(q)
        wall = time.perf_counter() - t0
        chunks = out.get("chunks") or []
        blob = "\n".join((c.get("text") or "") for c in chunks).lower()
        ok = all(n.lower() in blob for n in needles)
        if not ok:
            all_ok = False
        top = chunks[0] if chunks else {}
        print("\nQ:", q)
        print("retrieval_time_ms:", out.get("retrieval_time_ms"), "wall_s:", round(wall, 2), "chunks:", len(chunks))
        print("expected:", needles, "=>", "OK" if ok else "MISSING")
        print("top:", top.get("file"), top.get("chunk_id"), "score:", top.get("score"))
        prev = (top.get("text") or "")[:360].replace("\n", " ")
        print("top_preview:", prev + ("…" if prev else ""))

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

