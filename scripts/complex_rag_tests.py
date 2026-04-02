#!/usr/bin/env python3
"""
Complex / adversarial RAG checks (retrieval only, no LLM).
Run after: docker compose up -d  and  curl http://127.0.0.1:8000/health

  wsl
  python3 /mnt/e/loomin-docs/scripts/complex_rag_tests.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
TOP_K = 6


def search(q: str) -> dict:
    body = json.dumps({"query": q, "top_k": TOP_K}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/rag/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def blob(out: dict) -> str:
    return "\n".join((c.get("text") or "") for c in (out.get("chunks") or [])).lower()


def main() -> int:
    try:
        with urllib.request.urlopen(f"{BASE}/health", timeout=15) as r:
            print("health:", r.read().decode())
    except Exception as e:
        print("FAIL: API not up — start stack first:", e, file=sys.stderr)
        return 1

    # (query, must_all_substrings OR None, must_any_patterns regex, note)
    cases: list[tuple[str, list[str] | None, list[str] | None, str]] = [
        (
            "Compare Luna and Kai: who is the fairy vs who is the boy with the journal?",
            None,
            [r"luna", r"kai", r"journal"],
            "Cross-doc: both names + journal should appear somewhere in top-k.",
        ),
        (
            "Sweet Dreams Publishing title page illustrator",
            ["sweet dreams", "publishing"],
            None,
            "Lexical / title-line retrieval (BM25 helps).",
        ),
        (
            "Emma cottage enchanted forest golden curls blue eyes Mr Whiskers",
            ["cottage", "emma", "whisker"],
            None,
            "Packed factual query (many constraints).",
        ),
        (
            "Theron Guardian of Stories Chronicle Guardian Realm balance threatened",
            ["theron", "guardian realm"],
            None,
            "Kai Ch2 exposition.",
        ),
        (
            "Stardust unicorn Whisper owl Shimmer phoenix Dream Guardians",
            ["stardust", "whisper", "shimmer"],
            None,
            "Multi-entity Luna Ch4.",
        ),
        (
            "What is NOT in the story: Harry Potter Hogwarts",
            None,
            None,
            "Negative probe: model must not invent; retrieval should return unrelated Luna/Kai chunks, not HP names.",
        ),
    ]

    ok_all = True
    for q, needles, any_rx, note in cases:
        print("\n" + "=" * 72)
        print("NOTE:", note)
        print("Q:", q)
        t0 = time.perf_counter()
        try:
            out = search(q)
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, e.read().decode()[:400])
            ok_all = False
            continue
        wall = time.perf_counter() - t0
        b = blob(out)
        print(f"retrieval_ms={out.get('retrieval_time_ms')} wall_s={wall:.2f} chunks={len(out.get('chunks') or [])}")

        bad_hallucination_terms = ["harry potter", "hogwarts"]
        if "NOT in the story" in q:
            leaked = [t for t in bad_hallucination_terms if t in b]
            if leaked:
                print("WEAK: retrieved chunks mention unrelated franchise terms:", leaked)
                ok_all = False
            else:
                print("OK: no Harry/Hogwarts in retrieved text (retrieval not polluted).")

        if needles:
            miss = [n for n in needles if n.lower() not in b]
            if miss:
                print("MISSING:", miss)
                ok_all = False
            else:
                print("OK: all required substrings present:", needles)

        if any_rx:
            hits = [p for p in any_rx if re.search(p, b)]
            if len(hits) < 2:
                print("WEAK: expected multiple doc signals; got:", hits)
                ok_all = False
            else:
                print("OK: cross-doc patterns matched:", hits)

        top = (out.get("chunks") or [{}])[0]
        prev = (top.get("text") or "")[:280].replace("\n", " ")
        print("top:", top.get("file"), top.get("chunk_id"))
        print("preview:", prev + "…")

    print("\n" + "=" * 72)
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
