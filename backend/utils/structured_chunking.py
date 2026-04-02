"""Chapter-aware segmentation before token chunking (PDF storybooks, manuals)."""

from __future__ import annotations

import re
from typing import List, Tuple

# "Chapter 1:", "CHAPTER 2.", etc. — start a new segment after a newline.
_CHAPTER_SPLIT = re.compile(r"\n(?=(?:Chapter|CHAPTER)\s+\d+[:.\s])", re.MULTILINE)


def segment_for_ingest(full_text: str) -> List[str]:
    """
    Split document into coarse segments: optional title/front block, then chapters.
    Single-segment fallback = whole text (legacy behavior).
    """
    text = (full_text or "").strip()
    if not text:
        return []

    parts = _CHAPTER_SPLIT.split(text)
    if len(parts) <= 1:
        return [text]

    segments: List[str] = []
    head = parts[0].strip()
    if head and len(head) >= 40:
        segments.append(head)
    for p in parts[1:]:
        p = p.strip()
        if p:
            segments.append(p)
    return segments if segments else [text]


def label_segment(segment_text: str, segment_index: int) -> str:
    """Light prefix so embeddings distinguish front matter vs body."""
    if segment_index == 0:
        return f"[Title & opening]\n{segment_text}"
    return segment_text
