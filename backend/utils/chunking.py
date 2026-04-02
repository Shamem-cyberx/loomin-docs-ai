"""Token-aware chunking aligned with embedding model tokenizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from transformers import AutoTokenizer


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    start_char: int
    end_char: int


def build_token_chunker(model_id: str) -> Callable[[str, int, int], List[TextChunk]]:
    """Return a chunker using the Hugging Face tokenizer for *model_id*."""
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    def chunk_text(text: str, target_tokens: int, overlap_tokens: int) -> List[TextChunk]:
        if not text.strip():
            return []
        enc = tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )
        ids: List[int] = enc["input_ids"]
        offsets: List[tuple[int, int]] = enc["offset_mapping"]
        if not ids:
            return []
        chunks: List[TextChunk] = []
        step = max(1, target_tokens - overlap_tokens)
        i = 0
        chunk_idx = 0
        while i < len(ids):
            end_tok = min(len(ids), i + target_tokens)
            start_char = int(offsets[i][0])
            end_char = int(offsets[end_tok - 1][1])
            raw = text[start_char:end_char]
            if not raw.strip():
                i += step
                continue
            chunks.append(
                TextChunk(
                    text=raw,
                    chunk_index=chunk_idx,
                    start_char=start_char,
                    end_char=end_char,
                )
            )
            chunk_idx += 1
            i += step
        return chunks

    return chunk_text
