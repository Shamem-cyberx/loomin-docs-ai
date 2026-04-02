#!/usr/bin/env python3
"""Print top chunk per query for SUBMISSION-VERIFICATION.md (stdout)."""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def search(q: str, top_k: int = 4) -> dict:
    body = json.dumps({"query": q, "top_k": top_k}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/rag/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> None:
    cases = [
        ("multi-1", "Who is Mr. Whiskers or Emma's stuffed toy?", 4),
        ("multi-2", "What is the Dream Jar made of and what is inside?", 4),
        ("multi-3", "Name the unicorn and the owl that help Luna.", 4),
        ("multi-4", "What is Shimmer?", 4),
        ("multi-5", "Where does Emma live? Cottage forest moonlit", 4),
        ("multi-6", "What color are Emma's eyes?", 4),
        ("multi-7", "Who is Luna and her title?", 4),
        ("multi-8", "Illustrated by or publishing on the title page?", 4),
        ("tgt-1", "Sweet Dreams Publishing illustrated by", 6),
        ("tgt-2", "Where does Emma live? cozy cottage edge of an enchanted forest", 6),
        ("tgt-3", "What color are Emma's eyes?", 6),
        ("tgt-4", "What object did Kai find in the attic?", 6),
        ("tgt-5", "What color are Kai's eyes?", 6),
        ("tgt-6", "Who is Theron and what is his title?", 6),
        ("cx-1", "Compare Luna and Kai: who is the fairy vs who is the boy with the journal?", 6),
        ("cx-2", "Sweet Dreams Publishing title page illustrator", 6),
        ("cx-3", "Emma cottage enchanted forest golden curls blue eyes Mr Whiskers", 6),
        ("cx-4", "Theron Guardian of Stories Chronicle Guardian Realm balance threatened", 6),
        ("cx-5", "Stardust unicorn Whisper owl Shimmer phoenix Dream Guardians", 6),
        ("cx-6", "What is NOT in the story: Harry Potter Hogwarts", 6),
    ]
    for key, q, k in cases:
        out = search(q, k)
        top = (out.get("chunks") or [{}])[0]
        text = (top.get("text") or "").replace("\n", " ").strip()
        print(f"KEY={key}")
        print(f"Q={q!r}")
        print(f"MS={out.get('retrieval_time_ms')}")
        print(f"FILE={top.get('file')}")
        print(f"CHUNK={top.get('chunk_id')}")
        print(f"SCORE={top.get('score')}")
        print(f"TEXT={text[:1200]}")
        print("---")


if __name__ == "__main__":
    main()
