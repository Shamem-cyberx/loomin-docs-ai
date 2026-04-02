"""Process-wide SentenceTransformer (one load; shared by ingest + retrieve)."""

from __future__ import annotations

import logging
import threading
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_model: Optional[SentenceTransformer] = None


def get_sentence_transformer() -> SentenceTransformer:
    global _model
    with _lock:
        if _model is None:
            logger.info("loading sentence transformer", extra={"model": settings.embedding_model_id})
            _model = SentenceTransformer(settings.embedding_model_id)
        return _model


def encode_texts(texts: List[str], batch_size: int = 64) -> np.ndarray:
    """Batch-encode for much faster ingest than one-by-one encode calls."""
    if not texts:
        return np.zeros((0, 1), dtype=np.float32)
    enc = get_sentence_transformer()
    return enc.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype("float32")
