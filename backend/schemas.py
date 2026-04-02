"""API response schemas (mandatory structured JSON for LLM-backed routes)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    file: str
    chunk_id: str
    text: str


class LoominResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    request_id: str
    retrieval_time_ms: int = 0
    generation_speed_tps: float = 0.0
    llm_latency_ms: Optional[int] = None
    context_usage_percent: Optional[float] = None
    session_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    use_rag: bool = True
    model: Optional[str] = None


class EditRequest(BaseModel):
    selection: str
    action: str  # summarize | improve
    model: Optional[str] = None
    document_html: Optional[str] = None


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[List[Citation]] = None
    request_id: Optional[str] = None
    created_at: str


class ChatSessionOut(BaseModel):
    id: str
    title: Optional[str]
    messages: List[ChatMessageOut]


class RagSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = None


class RagChunkOut(BaseModel):
    file: str
    chunk_id: str
    text: str
    score: float


class RagSearchResponse(BaseModel):
    retrieval_time_ms: int
    chunks: List[RagChunkOut]
