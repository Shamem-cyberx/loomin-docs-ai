#!/usr/bin/env python3
"""
Offline RAG faithfulness smoke test.
 1) Ingests a tiny fixture.
 2) Retrieves context for a fixed question.
 3) Optionally calls Ollama; verifies non-trivial tokens from the answer appear in retrieved text.

Exit code 0 => PASS, 1 => FAIL.

Usage:
  DATA_DIR=./.rag_test_data python test_rag.py
  SKIP_OLLAMA=1 DATA_DIR=./.rag_test_data python test_rag.py
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DATA_DIR", str(ROOT / ".rag_test_data"))
os.environ.setdefault("OLLAMA_BASE_URL", os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))

from config import settings  # noqa: E402
from rag.ingest import ingest_file  # noqa: E402
from rag.retrieve import rag_index  # noqa: E402
from services.ollama import OllamaError, generate  # noqa: E402
from utils.pii_mask import mask_pii  # noqa: E402


FIXTURE = ROOT / "fixtures" / "sample_corpus.txt"
QUESTION = "What is the codename and region for the Loomin project?"
EXPECTED_SUBSTRINGS = ("LOOMIN-7", "Arctic")


def _tokenize(s: str) -> set[str]:
    return {w for w in re.findall(r"[A-Za-z0-9_-]{4,}", s.lower()) if len(w) >= 4}


def faithfulness(answer: str, chunk_texts: list[str]) -> bool:
    """Heuristic: majority of significant answer tokens appear in retrieved blob."""
    blob = " ".join(chunk_texts).lower()
    ans_tokens = _tokenize(answer)
    if len(ans_tokens) < 2:
        return False
    hits = sum(1 for t in ans_tokens if t in blob)
    return hits / len(ans_tokens) >= 0.6


def main() -> int:
    data = Path(settings.data_dir)
    if data.exists():
        shutil.rmtree(data)
    data.mkdir(parents=True, exist_ok=True)
    (data / settings.uploads_subdir).mkdir(parents=True, exist_ok=True)

    if not FIXTURE.is_file():
        print(f"FAIL — missing fixture {FIXTURE}")
        return 1

    stored = data / "uploads" / f"{uuid.uuid4()}_{FIXTURE.name}"
    shutil.copy(FIXTURE, stored)
    ingest_file(stored, FIXTURE.name, str(uuid.uuid4()))
    rag_index.reload()

    chunks, ms = rag_index.search(QUESTION, settings.rag_top_k)
    texts = [c.text for c in chunks]
    blob = " ".join(texts)
    for needle in EXPECTED_SUBSTRINGS:
        if needle.lower() not in blob.lower():
            print(f"FAIL — retrieval missing expected fact {needle!r} (retrieval {ms} ms)")
            return 1

    if os.environ.get("SKIP_OLLAMA", "").lower() in {"1", "true", "yes"}:
        print(f"PASS (retrieval only, {ms} ms) — SKIP_OLLAMA set")
        return 0

    context_blocks = [f"[{i}] {t.text}" for i, t in enumerate(chunks, start=1)]
    context_str = "\n".join(context_blocks)
    system = (
        "Answer ONLY from the provided context. If the answer is not present, say 'I don't know.'"
    )
    user = f"Context:\n{mask_pii(context_str)}\n\nQuestion:\n{mask_pii(QUESTION)}"
    try:
        result = generate(user, os.environ.get("OLLAMA_MODEL", "llama3"), system=system)
    except OllamaError as e:
        print(f"FAIL — Ollama unavailable ({e}); set SKIP_OLLAMA=1 for retrieval-only PASS")
        return 1

    answer = result.get("answer") or ""
    if "don't know" in answer.lower() and any(x.lower() in answer.lower() for x in EXPECTED_SUBSTRINGS):
        print("FAIL — contradictory answer")
        return 1

    ok = faithfulness(answer, texts)
    if ok:
        print(
            f"PASS — faithfulness ok (retrieval {ms} ms, llm {result.get('generation_speed_tps', 0):.2f} tok/s)"
        )
        return 0
    print(f"FAIL — answer not grounded in chunks:\n---\n{answer}\n---")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
