#!/usr/bin/env python3
"""Run many /api/rag/search queries; print live results. WSL: python3 scripts/multi_query_rag_test.py"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"
TOP_K = 4

# Post-retrieval substring hints (PDF story); labels are heuristic only — real evidence is the printed chunks.
CHECKS: list[tuple[str, list[str]]] = [
    ("Who is Mr. Whiskers or Emma's stuffed toy?", ["whisker", "rabbit", "stuffed"]),
    ("What is the Dream Jar made of and what is inside?", ["crystal", "dream"]),
    ("Name the unicorn and the owl that help Luna.", ["stardust", "whisper"]),
    ("What is Shimmer?", ["phoenix", "light"]),
    ("Where does Emma live? Cottage forest moonlit", ["cottage", "forest"]),
    ("What color are Emma's eyes?", ["blue"]),
    ("Who is Luna and her title?", ["luna", "dream keeper"]),
    ("Illustrated by or publishing on the title page?", ["sweet", "publishing"]),
]

def post_search(query: str) -> dict:
    body = json.dumps({"query": query, "top_k": TOP_K}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/rag/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    try:
        with urllib.request.urlopen(f"{BASE}/health", timeout=15) as r:
            print("health:", r.read().decode())
    except Exception as e:
        print("ERROR: API not up:", e, file=sys.stderr)
        return 1

    print("=" * 72)
    print("LIVE /api/rag/search results (chunks come from FAISS + your library PDFs)")
    print("=" * 72)

    all_ok = True
    for i, (question, expect_substrings) in enumerate(CHECKS, 1):
        print(f"\n>>> QUERY {i}: {question!r}")
        try:
            out = post_search(question)
        except Exception as e:
            print("  REQUEST FAILED:", e)
            all_ok = False
            continue
        ms = out.get("retrieval_time_ms")
        chunks = out.get("chunks") or []
        print(f"  retrieval_time_ms: {ms}  |  chunks_returned: {len(chunks)}")
        if not chunks:
            print("  ACCURACY vs PDF: FAIL (no chunks)")
            all_ok = False
            continue
        blob = "\n".join(c.get("text") or "" for c in chunks)
        blob_l = blob.lower()
        missing = [s for s in expect_substrings if s.lower() not in blob_l]
        if missing:
            print(f"  HEURISTIC vs PDF: review — substring check missed {missing} (chunk may still be relevant)")
            all_ok = False
        else:
            print(f"  HEURISTIC vs PDF: OK — top-{TOP_K} text includes: {expect_substrings}")
        top = chunks[0]
        preview = (top.get("text") or "")[:480].replace("\n", " ")
        print(f"  top_score: {top.get('score')}  file: {top.get('file')}  chunk: {top.get('chunk_id')}")
        print(f"  top_chunk_preview: {preview}…")

    print("\n" + "=" * 72)
    print("Note: This tests RETRIEVAL grounding in the indexed PDF text, not the LLM paraphrase.")
    print("Assessment RAG requirement = relevant chunks + citations; LLM must stay faithful to those chunks.")
    print("=" * 72)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
