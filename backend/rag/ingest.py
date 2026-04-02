"""Ingest PDF/TXT/MD: extract → chunk → embed → FAISS + JSONL metadata."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, Dict, List

import faiss
import fitz  # PyMuPDF
import numpy as np

from config import settings
from utils.chunking import TextChunk, build_token_chunker
from utils.structured_chunking import label_segment, segment_for_ingest

from .embeddings import encode_texts, get_sentence_transformer
from .retrieve import rag_index

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _sanitize_stem(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem)
    return base[:180] if base else "file"


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        doc = fitz.open(path)
        parts: List[str] = []
        try:
            for page in doc:
                parts.append(page.get_text("text") or "")
        finally:
            doc.close()
        return "\n".join(parts)
    if suffix in {".txt", ".md", ".markdown"}:
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix}")


def ingest_file(
    stored_path: Path,
    logical_filename: str,
    file_id: str,
) -> Dict[str, Any]:
    """
    Build or append to global FAISS index for one file.
    Uses inner product on L2-normalized vectors (cosine similarity).
    """
    text = extract_text(stored_path)
    if not text.strip():
        return {"chunks": 0, "message": "empty document"}

    chunker = build_token_chunker(settings.embedding_model_id)
    target = min(settings.chunk_target_tokens, 256)
    overlap = min(settings.chunk_overlap_tokens, target // 2)

    segments = segment_for_ingest(text) if settings.rag_structured_segments else [text]
    get_sentence_transformer()
    stem = _sanitize_stem(logical_filename)

    rows: List[Dict[str, Any]] = []
    texts: List[str] = []
    global_idx = 0
    for seg_i, segment in enumerate(segments):
        labeled = (
            label_segment(segment, seg_i)
            if settings.rag_structured_segments and len(segments) > 1
            else segment
        )
        raw_chunks: List[TextChunk] = chunker(labeled, target, overlap)
        for ch in raw_chunks:
            cid = f"{stem}:{file_id[:8]}:{global_idx}"
            rows.append(
                {
                    "file": logical_filename,
                    "upload_id": file_id,
                    "chunk_id": cid,
                    "text": ch.text,
                }
            )
            texts.append(ch.text)
            global_idx += 1

    if not texts:
        return {"chunks": 0, "message": "no chunks after tokenization"}

    new_mat = encode_texts(texts, batch_size=settings.embedding_encode_batch_size)
    meta_path = settings.data_dir / settings.faiss_meta_name
    index_path = settings.data_dir / settings.faiss_index_name
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    with _lock:
        dim = new_mat.shape[1]
        if index_path.exists() and meta_path.exists():
            index = faiss.read_index(str(index_path))
            if index.d != dim:
                raise RuntimeError("Embedding dimension mismatch; rebuild index or clear data directory")
            with meta_path.open("r", encoding="utf-8") as f:
                existing_meta = [json.loads(l) for l in f if l.strip()]
            # Drop previous chunks for this upload (re-ingest) or legacy same-name rows
            keep_idx = [
                i
                for i, m in enumerate(existing_meta)
                if not (
                    m.get("upload_id") == file_id
                    or (
                        not m.get("upload_id")
                        and m.get("file") == logical_filename
                    )
                )
            ]
            if keep_idx:
                # Rebuild index from kept rows — simple production path for SQLite-scale corpora
                kept_meta = [existing_meta[i] for i in keep_idx]
                # Retrieve vectors for kept rows by re-encoding (avoids storing all vectors on disk)
                enc_texts = [m["text"] for m in kept_meta]
                kept_mat = encode_texts(enc_texts, batch_size=settings.embedding_encode_batch_size)
                merged_mat = np.vstack([kept_mat, new_mat])
                merged_meta = kept_meta + rows
            else:
                merged_mat = new_mat
                merged_meta = rows
        else:
            merged_mat = new_mat
            merged_meta = rows

        index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(merged_mat)
        index.add(merged_mat)
        faiss.write_index(index, str(index_path))
        with meta_path.open("w", encoding="utf-8") as f:
            for m in merged_meta:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

    rag_index.reload()
    logger.info(
        "ingest complete",
        extra={"file": logical_filename, "chunks": len(rows)},
    )
    return {"chunks": len(rows), "file": logical_filename}


def purge_vectors_for_upload(upload_id: str, logical_filename: str) -> Dict[str, Any]:
    """Remove all vector rows for one upload (by id; legacy rows matched by filename)."""
    meta_path = settings.data_dir / settings.faiss_meta_name
    index_path = settings.data_dir / settings.faiss_index_name
    if not meta_path.exists() or not index_path.exists():
        rag_index.reload()
        return {"removed_chunks": 0, "rebuilt": False}

    with _lock:
        with meta_path.open("r", encoding="utf-8") as f:
            existing_meta = [json.loads(l) for l in f if l.strip()]

        def _keep(m: Dict[str, Any]) -> bool:
            if m.get("upload_id") == upload_id:
                return False
            if not m.get("upload_id") and m.get("file") == logical_filename:
                return False
            return True

        kept_meta = [m for m in existing_meta if _keep(m)]
        removed = len(existing_meta) - len(kept_meta)
        if removed <= 0:
            rag_index.reload()
            return {"removed_chunks": 0, "rebuilt": False}

        if not kept_meta:
            index_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            rag_index.reload()
            logger.info(
                "purge removed all chunks",
                extra={"upload_id": upload_id, "file": logical_filename, "removed": removed},
            )
            return {"removed_chunks": removed, "rebuilt": True, "remaining_chunks": 0}

        get_sentence_transformer()
        enc_texts = [m["text"] for m in kept_meta]
        kept_mat = encode_texts(enc_texts, batch_size=settings.embedding_encode_batch_size)
        dim = kept_mat.shape[1]
        index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(kept_mat)
        index.add(kept_mat)
        faiss.write_index(index, str(index_path))
        with meta_path.open("w", encoding="utf-8") as f:
            for m in kept_meta:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

    rag_index.reload()
    logger.info(
        "purge complete",
        extra={"upload_id": upload_id, "file": logical_filename, "removed": removed, "kept": len(kept_meta)},
    )
    return {"removed_chunks": removed, "rebuilt": True, "remaining_chunks": len(kept_meta)}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()
