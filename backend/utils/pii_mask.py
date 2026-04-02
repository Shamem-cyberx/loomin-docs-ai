"""Mask PII before LLM calls (regex-based, no external PII services)."""

from __future__ import annotations

import re

_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.I,
)
# E.164-ish and common US formats; conservative to reduce false negatives
_PHONE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"
    r"|\b\d{10,15}\b",
)
# API keys: long alphanumeric/dash/underscore tokens often labeled
_API_KEY = re.compile(
    r"\b(?:api[_-]?key|token|secret|bearer)\s*[=:]\s*\"?([A-Za-z0-9_\-]{20,})\"?\b",
    re.I,
)
_STANDALONE_KEY = re.compile(r"\b(sk-[A-Za-z0-9]{20,}|[A-Za-z0-9]{32,})\b")


def mask_pii(text: str) -> str:
    """Replace emails, phones, and key-like strings with placeholders."""
    if not text:
        return text
    masked = _EMAIL.sub("[EMAIL_REDACTED]", text)
    masked = _PHONE.sub("[PHONE_REDACTED]", masked)

    def _repl_key(m: re.Match[str]) -> str:
        label = m.group(0).split("=", 1)[0].split(":", 1)[0].strip()
        return f'{label}="[API_KEY_REDACTED]"'

    masked = _API_KEY.sub(_repl_key, masked)
    masked = _STANDALONE_KEY.sub("[API_KEY_REDACTED]", masked)
    return masked
