"""Ollama /api/generate client with timing and tokens/sec."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client: Optional[httpx.Client] = None


def _http() -> httpx.Client:
    """Shared client with HTTP keep-alive (lower latency vs new connection per call)."""
    global _client
    tmax = max(float(settings.ollama_request_timeout_s), 60.0)
    with _client_lock:
        if _client is None:
            _client = httpx.Client(
                base_url=settings.ollama_base_url.rstrip("/"),
                timeout=httpx.Timeout(tmax, connect=60.0),
                limits=httpx.Limits(max_keepalive_connections=8, max_connections=16),
            )
        return _client


class OllamaError(RuntimeError):
    pass


def list_local_models(timeout_s: float = 10.0) -> list[str]:
    try:
        r = _http().get("/api/tags", timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPError as e:
        logger.warning("could not list ollama models: %s", e)
        return []
    models: list[str] = []
    for m in data.get("models") or []:
        name = m.get("name")
        if name:
            models.append(name)
    return models


def generate(
    prompt: str,
    model: str,
    *,
    system: Optional[str] = None,
    timeout_s: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Call Ollama generate (non-streaming). Returns dict with:
    answer, prompt_eval_count, eval_count, eval_duration_ns, total_duration_ns
    """
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
    }
    if system:
        payload["system"] = system

    opts: Dict[str, Any] = {}
    if settings.ollama_num_predict > 0:
        opts["num_predict"] = settings.ollama_num_predict
    if settings.ollama_num_ctx > 0:
        opts["num_ctx"] = settings.ollama_num_ctx
    if settings.ollama_num_thread > 0:
        opts["num_thread"] = settings.ollama_num_thread
    if opts:
        payload["options"] = opts

    tlim = float(timeout_s) if timeout_s is not None else float(settings.ollama_request_timeout_s)
    t0 = time.perf_counter()
    try:
        r = _http().post("/api/generate", json=payload, timeout=tlim)
        if r.status_code == 404:
            hint = (r.text or "")[:400].strip()
            raise OllamaError(
                f"Ollama 404 for model {model!r} — it may not be installed. "
                f"Try: docker compose exec ollama ollama pull llama3 "
                f"or create custom tags per deploy/modelfiles/. Server said: {hint or 'no body'}"
            )
        r.raise_for_status()
        body = r.json()
    except OllamaError:
        raise
    except httpx.HTTPError as e:
        logger.exception("ollama request failed")
        raise OllamaError(str(e)) from e

    total_s = time.perf_counter() - t0
    answer = (body.get("response") or "").strip()
    eval_count = int(body.get("eval_count") or 0)
    eval_duration_ns = float(body.get("eval_duration") or 0.0)
    prompt_eval_count = int(body.get("prompt_eval_count") or 0)

    gen_s = eval_duration_ns / 1e9 if eval_duration_ns else 0.0
    tps = (eval_count / gen_s) if gen_s > 0 and eval_count else 0.0

    return {
        "answer": answer,
        "prompt_eval_count": prompt_eval_count,
        "eval_count": eval_count,
        "eval_duration_ns": eval_duration_ns,
        "total_duration_s": total_s,
        "generation_speed_tps": float(tps),
        "raw": body,
    }


def warmup_model(model: Optional[str] = None, timeout_s: Optional[float] = None) -> None:
    """Tiny generate so weights stay loaded (uses keep_alive). Called from startup thread."""
    m = model or settings.default_ollama_model
    tlim = float(timeout_s) if timeout_s is not None else float(settings.ollama_request_timeout_s)
    payload: Dict[str, Any] = {
        "model": m,
        "prompt": "ping",
        "stream": False,
        "keep_alive": settings.ollama_keep_alive,
        "options": {"num_predict": 4, "num_ctx": min(512, settings.ollama_num_ctx or 512)},
    }
    try:
        r = _http().post("/api/generate", json=payload, timeout=tlim)
        if r.status_code == 404:
            logger.warning("ollama warmup skipped — model %r missing", m)
            return
        r.raise_for_status()
    except Exception as e:
        logger.warning("ollama warmup failed: %s", e)
