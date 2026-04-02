"""
Loomin-Docs API — FastAPI backend for offline RAG + Ollama.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from database import (
    ChatMessage,
    ChatSession,
    Document,
    DocumentVersion,
    SessionLocal,
    UploadedFile,
    init_db,
)
from rag.ingest import ingest_file, purge_vectors_for_upload, sha256_file
from rag.retrieve import RetrievedChunk, rag_index
from schemas import (
    ChatMessageOut,
    ChatRequest,
    ChatSessionOut,
    Citation,
    EditRequest,
    LoominResponse,
    RagChunkOut,
    RagSearchRequest,
    RagSearchResponse,
)
from services.ollama import OllamaError, generate, list_local_models, warmup_model
from utils.pii_mask import mask_pii

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("loomin")

CONTEXT_WINDOW_TOKENS = int(settings.context_window_tokens or 8192)


def _rough_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "")


def _rag_chunk_for_prompt(text: str) -> str:
    cap = settings.rag_prompt_max_chars_per_chunk
    if cap <= 0 or len(text) <= cap:
        return text
    return text[:cap] + "…"


def _build_rag_prompt(
    question: str,
    chunks: List[RetrievedChunk],
) -> tuple[str, str]:
    """Return (system, user) messages for Ollama."""
    context_blocks = []
    for i, c in enumerate(chunks, start=1):
        snippet = _rag_chunk_for_prompt(c.text)
        context_blocks.append(f"[{i}] (file={c.file}, chunk_id={c.chunk_id})\n{snippet}")
    context_str = "\n\n".join(context_blocks) if context_blocks else "(no context)"
    system = (
        "You are Loomin-Docs, a careful assistant. "
        "Answer ONLY from the provided context. "
        "If the answer is not present in the context, say exactly: I don't know."
    )
    user = (
        "Context:\n"
        f"{mask_pii(context_str)}\n\n"
        "Question:\n"
        f"{mask_pii(question)}\n\n"
        "Answer concisely using only the context."
    )
    return system, user


def _estimate_context_usage(
    *,
    editor_html: str,
    chunk_texts: List[str],
    prompt: str,
) -> float:
    doc_tok = _rough_tokens(_strip_html(editor_html))
    chunk_tok = sum(_rough_tokens(t) for t in chunk_texts)
    prompt_tok = _rough_tokens(prompt)
    total = doc_tok + chunk_tok + prompt_tok
    pct = min(100.0, (total / CONTEXT_WINDOW_TOKENS) * 100.0)
    return round(pct, 2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    (Path(settings.data_dir) / settings.uploads_subdir).mkdir(parents=True, exist_ok=True)
    init_db()
    rag_index.ensure_loaded()
    db = SessionLocal()
    try:
        if db.query(Document).count() == 0:
            db.add(Document(title="Main", editor_html="<p></p>"))
            db.commit()
    finally:
        db.close()

    if settings.warm_embeddings_on_startup or settings.warm_ollama_on_startup:

        def _warm_sequential() -> None:
            """MiniLM then Ollama in series — parallel warmups compete for CPU and stretch first-token time."""
            import time

            try:
                if settings.warm_embeddings_on_startup:
                    from rag.embeddings import encode_texts, get_sentence_transformer

                    get_sentence_transformer()
                    encode_texts(["__warmup__"], batch_size=1)
                    logger.info("embedding model warmed in background")
                if settings.warm_ollama_on_startup:
                    time.sleep(1)
                    warmup_model(settings.default_ollama_model)
                    logger.info(
                        "ollama warmup finished",
                        extra={"model": settings.default_ollama_model},
                    )
            except Exception as e:
                logger.warning("background warm failed: %s", e)

        threading.Thread(target=_warm_sequential, daemon=True).start()

    yield


app = FastAPI(title="Loomin-Docs API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/ready")
def ready():
    """Fast checks without running the LLM (use for smoke tests)."""
    models = list_local_models()
    idx = rag_index.snapshot()
    return {
        "api": "ok",
        "ollama_models": models,
        "ollama_reachable": bool(models),
        "rag": idx,
        "rag_ready": idx["meta_rows"] > 0,
        "note": "First LLM answer can take minutes on CPU while weights load; later requests are faster with keep_alive.",
    }


@app.get("/api/models")
def api_models():
    names = list_local_models()
    return {"models": names, "default": settings.default_ollama_model}


@app.get("/api/documents/default")
def get_default_doc(session: Session = Depends(get_db)):
    doc = session.query(Document).order_by(Document.updated_at.desc()).first()
    if not doc:
        raise HTTPException(404, "no document")
    return {"id": doc.id, "title": doc.title, "editor_html": doc.editor_html, "updated_at": doc.updated_at}


@app.put("/api/documents/default")
def put_default_doc(body: dict, session: Session = Depends(get_db)):
    doc = session.query(Document).order_by(Document.updated_at.desc()).first()
    if not doc:
        doc = Document(title="Main", editor_html="<p></p>")
        session.add(doc)
        session.flush()
    html = body.get("editor_html", doc.editor_html)
    doc.editor_html = html
    doc.title = body.get("title", doc.title)
    next_v = (session.query(DocumentVersion).filter_by(document_id=doc.id).count() or 0) + 1
    session.add(
        DocumentVersion(
            document_id=doc.id,
            version=next_v,
            editor_html=html,
        )
    )
    session.commit()
    return {"id": doc.id, "title": doc.title, "version": next_v}


@app.post("/api/files/upload")
async def upload_file(
    session: Session = Depends(get_db),
    upload: UploadFile = File(...),
):
    raw = await upload.read()
    digest = hashlib.sha256(raw).hexdigest()
    existing = (
        session.query(UploadedFile)
        .filter(UploadedFile.sha256 == digest, UploadedFile.ingest_status == "ready")
        .first()
    )
    if existing:
        return {
            "deduplicated": True,
            "existing_file_id": existing.id,
            "filename": existing.filename,
            "ingest_status": existing.ingest_status,
            "chunk_count": existing.chunk_count,
            "message": "Identical file (SHA-256) already indexed; duplicate vectors not added.",
        }

    file_id = str(uuid.uuid4())
    safe_name = Path(upload.filename or "upload").name
    dest_dir = settings.data_dir / settings.uploads_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{file_id}_{safe_name}"
    dest.write_bytes(raw)
    rec = UploadedFile(
        id=file_id,
        filename=safe_name,
        stored_path=str(dest),
        content_type=upload.content_type,
        sha256=digest,
        ingest_status="processing",
    )
    session.add(rec)
    session.commit()
    try:
        stats = ingest_file(dest, safe_name, file_id)
        rec.ingest_status = "ready"
        rec.chunk_count = stats.get("chunks")
    except Exception as e:
        logger.exception("ingest failed")
        rec.ingest_status = f"failed: {e}"
    session.commit()
    return {
        "id": rec.id,
        "filename": rec.filename,
        "ingest_status": rec.ingest_status,
        "chunk_count": rec.chunk_count,
    }


@app.get("/api/files")
def list_files(session: Session = Depends(get_db)):
    rows = session.query(UploadedFile).order_by(UploadedFile.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "ingest_status": r.ingest_status,
            "chunk_count": r.chunk_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@app.delete("/api/files/{file_id}")
def delete_uploaded_file(file_id: str, session: Session = Depends(get_db)):
    rec = session.get(UploadedFile, file_id)
    if not rec:
        raise HTTPException(404, "file not found")
    try:
        purge_vectors_for_upload(rec.id, rec.filename)
    except Exception as e:
        logger.exception("purge failed during file delete")
        raise HTTPException(500, f"index purge failed: {e}") from e
    path = Path(rec.stored_path)
    if path.exists():
        try:
            path.unlink()
        except OSError as e:
            logger.warning("could not delete stored file: %s", e)
    session.delete(rec)
    session.commit()
    return {"status": "deleted", "id": file_id}


@app.post("/api/files/{file_id}/reingest")
def reingest_file(file_id: str, session: Session = Depends(get_db)):
    rec = session.get(UploadedFile, file_id)
    if not rec:
        raise HTTPException(404, "file not found")
    path = Path(rec.stored_path)
    if not path.exists():
        raise HTTPException(400, "stored file missing on disk")
    rec.ingest_status = "processing"
    session.commit()
    try:
        stats = ingest_file(path, rec.filename, rec.id)
        rec.ingest_status = "ready"
        rec.chunk_count = stats.get("chunks")
    except Exception as e:
        logger.exception("reingest failed")
        rec.ingest_status = f"failed: {e}"
    session.commit()
    return {
        "id": rec.id,
        "filename": rec.filename,
        "ingest_status": rec.ingest_status,
        "chunk_count": rec.chunk_count,
    }


@app.post("/api/chat", response_model=LoominResponse)
def chat(req: ChatRequest, session: Session = Depends(get_db)):
    request_id = str(uuid.uuid4())
    model = req.model or settings.default_ollama_model
    retrieval_ms = 0
    citations: List[Citation] = []
    chunks: List[RetrievedChunk] = []

    if req.use_rag:
        chunks, retrieval_ms = rag_index.search(req.message, settings.rag_top_k)
        citations = [
            Citation(file=c.file, chunk_id=c.chunk_id, text=c.text[:2000]) for c in chunks
        ]

    system, user_prompt = _build_rag_prompt(req.message, chunks if req.use_rag else [])
    doc = session.query(Document).order_by(Document.updated_at.desc()).first()
    editor_html = doc.editor_html if doc else ""
    usage_pct = _estimate_context_usage(
        editor_html=editor_html,
        chunk_texts=[c.text for c in chunks],
        prompt=user_prompt + system,
    )

    try:
        result = generate(user_prompt, model, system=system)
    except OllamaError as e:
        raise HTTPException(502, f"ollama error: {e}") from e

    answer = result["answer"]
    llm_ms = int((result.get("total_duration_s") or 0) * 1000)
    tps = float(result.get("generation_speed_tps") or 0.0)

    sess_id = req.session_id
    if not sess_id:
        s = None
    else:
        s = session.get(ChatSession, sess_id)
    if not s:
        # Stale browser localStorage after DB/volume reset — create a session instead of 404
        title = (req.message[:80] + "…") if len(req.message) > 80 else req.message
        s = ChatSession(title=title)
        session.add(s)
        session.flush()
        sess_id = s.id

    session.add(
        ChatMessage(
            session_id=sess_id,
            role="user",
            content=req.message,
            request_id=request_id,
        )
    )
    payload = LoominResponse(
        answer=answer,
        citations=citations if req.use_rag else [],
        request_id=request_id,
        retrieval_time_ms=retrieval_ms,
        generation_speed_tps=tps,
        llm_latency_ms=llm_ms,
        context_usage_percent=usage_pct,
        session_id=sess_id,
    )
    session.add(
        ChatMessage(
            session_id=sess_id,
            role="assistant",
            content=payload.answer,
            citations=[c.model_dump() for c in payload.citations],
            structured_response=payload.model_dump(),
            request_id=request_id,
        )
    )
    session.commit()
    return payload


@app.post("/api/chat/general", response_model=LoominResponse)
def chat_general(req: ChatRequest, session: Session = Depends(get_db)):
    """General Q&A without RAG retrieval (still applies PII masking)."""
    request_id = str(uuid.uuid4())
    model = req.model or settings.default_ollama_model
    system = (
        "You are a helpful local assistant running fully offline. "
        "Be concise and accurate. If you lack information, say you don't know."
    )
    user_prompt = mask_pii(req.message)
    doc = session.query(Document).order_by(Document.updated_at.desc()).first()
    editor_html = doc.editor_html if doc else ""
    usage_pct = _estimate_context_usage(
        editor_html=editor_html,
        chunk_texts=[],
        prompt=user_prompt + system,
    )
    try:
        result = generate(user_prompt, model, system=system)
    except OllamaError as e:
        raise HTTPException(502, f"ollama error: {e}") from e

    answer = result["answer"]
    llm_ms = int((result.get("total_duration_s") or 0) * 1000)
    tps = float(result.get("generation_speed_tps") or 0.0)

    sess_id = req.session_id
    if not sess_id:
        s = None
    else:
        s = session.get(ChatSession, sess_id)
    if not s:
        s = ChatSession(title=req.message[:80])
        session.add(s)
        session.flush()
        sess_id = s.id

    session.add(ChatMessage(session_id=sess_id, role="user", content=req.message, request_id=request_id))
    payload = LoominResponse(
        answer=answer,
        citations=[],
        request_id=request_id,
        retrieval_time_ms=0,
        generation_speed_tps=tps,
        llm_latency_ms=llm_ms,
        context_usage_percent=usage_pct,
        session_id=sess_id,
    )
    session.add(
        ChatMessage(
            session_id=sess_id,
            role="assistant",
            content=payload.answer,
            structured_response=payload.model_dump(),
            request_id=request_id,
        )
    )
    session.commit()
    return payload


@app.post("/api/edit/selection", response_model=LoominResponse)
def edit_selection(req: EditRequest, session: Session = Depends(get_db)):
    request_id = str(uuid.uuid4())
    model = req.model or settings.default_ollama_model
    action = req.action.lower().strip()
    if action not in {"summarize", "improve"}:
        raise HTTPException(400, "action must be summarize or improve")

    doc_ctx = _strip_html(req.document_html or "")
    instruction = (
        "Summarize the selection in clear prose while preserving meaning."
        if action == "summarize"
        else "Improve clarity and grammar of the selection; keep the same voice and facts."
    )
    system = "You rewrite text for a document editor. Output ONLY the replacement text, no quotes or preamble."
    user = (
        f"{instruction}\n\n"
        f"Document context (may be empty):\n{mask_pii(doc_ctx[:4000])}\n\n"
        f"Selection:\n{mask_pii(req.selection)}"
    )
    try:
        result = generate(user, model, system=system)
    except OllamaError as e:
        raise HTTPException(502, f"ollama error: {e}") from e

    answer = result["answer"].strip()
    llm_ms = int((result.get("total_duration_s") or 0) * 1000)
    tps = float(result.get("generation_speed_tps") or 0.0)
    usage_pct = _estimate_context_usage(
        editor_html=req.document_html or "",
        chunk_texts=[],
        prompt=user + system,
    )
    return LoominResponse(
        answer=answer,
        citations=[],
        request_id=request_id,
        retrieval_time_ms=0,
        generation_speed_tps=tps,
        llm_latency_ms=llm_ms,
        context_usage_percent=usage_pct,
    )


@app.get("/api/chat/sessions/{session_id}", response_model=ChatSessionOut)
def get_session_messages(session_id: str, session: Session = Depends(get_db)):
    s = session.get(ChatSession, session_id)
    if not s:
        raise HTTPException(404, "session not found")
    msgs: List[ChatMessageOut] = []
    for m in sorted(s.messages, key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.min)):
        cites = None
        if m.citations:
            cites = [Citation.model_validate(c) for c in m.citations]
        msgs.append(
            ChatMessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                citations=cites,
                request_id=m.request_id,
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
        )
    return ChatSessionOut(id=s.id, title=s.title, messages=msgs)


@app.post("/api/chat/sessions")
def new_session(session: Session = Depends(get_db)):
    s = ChatSession(title="New chat")
    session.add(s)
    session.commit()
    return {"id": s.id}


@app.get("/api/rag/status")
def rag_status():
    idx = rag_index.snapshot()
    p = settings.data_dir / settings.faiss_index_name
    return {
        "index_exists": p.exists(),
        "path": str(p),
        "faiss_vectors": idx["faiss_vectors"],
        "meta_rows": idx["meta_rows"],
    }


@app.post("/api/rag/search", response_model=RagSearchResponse)
def rag_search(body: RagSearchRequest):
    """
    Retrieve top chunks for a query — no LLM call. Use for fast tests or debugging retrieval.
    Typical wall time: sub-second after the embedding model is loaded in RAM.
    """
    q = (body.query or "").strip()
    if not q:
        raise HTTPException(400, "query is required")
    k = body.top_k if body.top_k is not None else settings.rag_top_k
    chunks, ms = rag_index.search(q, k)
    return RagSearchResponse(
        retrieval_time_ms=ms,
        chunks=[
            RagChunkOut(file=c.file, chunk_id=c.chunk_id, text=c.text, score=c.score)
            for c in chunks
        ],
    )
