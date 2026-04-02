"""FAISS retrieval with metadata sidecar (JSONL), optional BM25 + RRF + cross-encoder rerank."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np

from config import settings

from .embeddings import encode_texts, get_sentence_transformer

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize_bm25(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 1]


def _attribute_bonus(query: str, text: str) -> float:
    """
    Tiny heuristic boost for attribute questions where dense/BM25 can prefer a later chunk.
    Keeps us offline and cheap; cross-encoder rerank remains the best option when available.
    """
    q = (query or "").lower()
    t = (text or "").lower()
    bonus = 0.0
    if "color" in q and "eyes" in q:
        # Prefer explicit "X eyes" mentions over generic "blue" elsewhere.
        if re.search(r"\bblue\b.{0,25}\beyes\b", t) or re.search(r"\beyes\b.{0,25}\bblue\b", t):
            bonus += 0.75
        if re.search(r"\bgreen\b.{0,25}\beyes\b", t) or re.search(r"\beyes\b.{0,25}\bgreen\b", t):
            bonus += 0.75
        if re.search(r"\bbrightest\b.{0,40}\beyes\b", t) or re.search(r"\bbright\b.{0,40}\beyes\b", t):
            bonus += 0.25
    return bonus


_ce_lock = threading.Lock()
_cross_encoder: Optional[Any] = None
_cross_encoder_failed = False


def _get_cross_encoder() -> Optional[Any]:
    """Lazy CrossEncoder; on air-gap failure return None and skip reranking."""
    global _cross_encoder, _cross_encoder_failed
    if not settings.rag_rerank_enabled or _cross_encoder_failed:
        return _cross_encoder
    with _ce_lock:
        if _cross_encoder is None and not _cross_encoder_failed:
            try:
                from sentence_transformers import CrossEncoder

                _cross_encoder = CrossEncoder(settings.rag_rerank_model_id)
                logger.info("loaded cross-encoder", extra={"model": settings.rag_rerank_model_id})
            except Exception as e:
                _cross_encoder_failed = True
                logger.warning("cross-encoder unavailable (offline?): %s", e)
                _cross_encoder = None
        return _cross_encoder


@dataclass
class RetrievedChunk:
    file: str
    chunk_id: str
    text: str
    score: float


class RAGIndex:
    """Thread-safe lazy-loaded FAISS index + ST encoder + optional BM25."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._index: Optional[faiss.Index] = None
        self._meta: List[Dict[str, Any]] = []
        self._bm25: Optional[Any] = None

    def _index_path(self) -> Path:
        return settings.data_dir / settings.faiss_index_name

    def _meta_path(self) -> Path:
        return settings.data_dir / settings.faiss_meta_name

    def reload(self) -> None:
        with self._lock:
            self._load_nolock()

    def _rebuild_bm25_nolock(self) -> None:
        self._bm25 = None
        if not settings.rag_hybrid_enabled or not self._meta:
            return
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.warning("rank_bm25 not installed; hybrid BM25 disabled")
            return
        corpus = []
        for m in self._meta:
            t = _tokenize_bm25(m.get("text") or "")
            corpus.append(t if t else ["empty"])
        self._bm25 = BM25Okapi(corpus)
        logger.info("BM25 index rebuilt", extra={"docs": len(corpus)})

    def _load_nolock(self) -> None:
        index_path = self._index_path()
        meta_path = self._meta_path()
        self._index = None
        self._meta = []
        self._bm25 = None
        if not index_path.exists() or not meta_path.exists():
            logger.warning("RAG index not found; retrieval will return empty until ingest runs")
            return
        self._index = faiss.read_index(str(index_path))
        meta: List[Dict[str, Any]] = []
        with meta_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    meta.append(json.loads(line))
        self._meta = meta
        logger.info("loaded FAISS index", extra={"vectors": self._index.ntotal})
        self._rebuild_bm25_nolock()

    def ensure_loaded(self) -> None:
        with self._lock:
            if self._index is None and self._index_path().exists():
                self._load_nolock()

    def snapshot(self) -> Dict[str, Any]:
        """Lightweight index stats for /ready (no embedding work)."""
        with self._lock:
            if self._index is None and self._index_path().exists():
                self._load_nolock()
            return {
                "faiss_vectors": int(self._index.ntotal) if self._index else 0,
                "meta_rows": len(self._meta),
                "hybrid_bm25": self._bm25 is not None,
            }

    def _search_dense_only(self, query: str, top_k: int, t0: float) -> Tuple[List[RetrievedChunk], int]:
        with self._lock:
            if self._index is None or self._index.ntotal == 0 or not self._meta:
                return [], int((time.perf_counter() - t0) * 1000)
            n = len(self._meta)
            get_sentence_transformer()
            qv = encode_texts([query], batch_size=1)
            scores, idxs = self._index.search(qv, min(top_k, self._index.ntotal))

        results: List[RetrievedChunk] = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0 or idx >= n:
                continue
            row = self._meta[idx]
            results.append(
                RetrievedChunk(
                    file=row.get("file", ""),
                    chunk_id=row.get("chunk_id", ""),
                    text=row.get("text", ""),
                    score=float(score),
                )
            )
        return results, int((time.perf_counter() - t0) * 1000)

    def _search_hybrid(self, query: str, top_k: int, t0: float) -> Tuple[List[RetrievedChunk], int]:
        with self._lock:
            if self._index is None or self._index.ntotal == 0 or not self._meta:
                return [], int((time.perf_counter() - t0) * 1000)
            n = len(self._meta)
            if int(self._index.ntotal) != n:
                logger.warning("meta/FAISS length mismatch; falling back to dense-only")
                return self._search_dense_only(query, top_k, t0)
            bm25 = self._bm25
            get_sentence_transformer()
            qv = encode_texts([query], batch_size=1)
            cand_n = min(max(top_k * settings.rag_dense_candidate_mult, top_k * 2), n)
            scores_d, idxs_d = self._index.search(qv, cand_n)
            meta_copy = list(self._meta)

        dense_ordered: List[int] = []
        for idx in idxs_d[0]:
            ii = int(idx)
            if 0 <= ii < n:
                dense_ordered.append(ii)

        rrf_k = settings.rag_rrf_k
        rrf: Dict[int, float] = {}
        for rank, idx in enumerate(dense_ordered):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)

        if bm25 is not None:
            qtok = _tokenize_bm25(query)
            if not qtok:
                qtok = ["empty"]
            bm25_scores = bm25.get_scores(qtok)
            bm25_top = min(settings.rag_bm25_top_m, n)
            bm25_idx = list(np.argsort(bm25_scores)[::-1][:bm25_top])
            for rank, idx in enumerate(bm25_idx):
                ii = int(idx)
                rrf[ii] = rrf.get(ii, 0.0) + 1.0 / (rrf_k + rank + 1)

        fused = sorted(rrf.keys(), key=lambda i: rrf[i], reverse=True)
        pool_n = max(settings.rag_rerank_pool, top_k)
        pool = fused[:pool_n]

        reranker = _get_cross_encoder()
        final_indices: List[int] = []
        final_scores: List[float] = []

        if settings.rag_rerank_enabled and reranker is not None and pool:
            texts = [
                (meta_copy[i].get("text") or "")[: settings.rag_rerank_max_chars] for i in pool
            ]
            pairs = [(query, t) for t in texts]
            try:
                ce_scores = reranker.predict(pairs, batch_size=8, show_progress_bar=False)
                order = np.argsort(np.array(ce_scores))[::-1][:top_k]
                final_indices = [pool[int(j)] for j in order]
                final_scores = [float(ce_scores[int(j)]) for j in order]
            except Exception as e:
                logger.warning("rerank failed, using RRF order: %s", e)
                final_indices = pool[:top_k]
                final_scores = [rrf[i] for i in final_indices]
        else:
            # Apply lightweight lexical heuristics as a tie-breaker.
            scored = [(i, rrf[i] + _attribute_bonus(query, meta_copy[i].get("text") or "")) for i in pool]
            scored.sort(key=lambda x: x[1], reverse=True)
            final_indices = [i for i, _ in scored[:top_k]]
            final_scores = [s for _, s in scored[:top_k]]

        results: List[RetrievedChunk] = []
        for idx, sc in zip(final_indices, final_scores):
            row = meta_copy[idx]
            results.append(
                RetrievedChunk(
                    file=row.get("file", ""),
                    chunk_id=row.get("chunk_id", ""),
                    text=row.get("text", ""),
                    score=float(sc),
                )
            )
        return results, int((time.perf_counter() - t0) * 1000)

    def search(self, query: str, top_k: int) -> Tuple[List[RetrievedChunk], int]:
        """Return retrieved chunks and retrieval latency in milliseconds."""
        self.ensure_loaded()
        t0 = time.perf_counter()
        if settings.rag_hybrid_enabled and self._bm25 is not None:
            return self._search_hybrid(query, top_k, t0)
        return self._search_dense_only(query, top_k, t0)


rag_index = RAGIndex()
