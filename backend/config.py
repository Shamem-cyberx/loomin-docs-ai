"""Application configuration (env-driven for Docker and air-gapped deploys)."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = Path("/data")
    uploads_subdir: str = "uploads"
    faiss_index_name: str = "faiss.index"
    faiss_meta_name: str = "faiss_meta.jsonl"

    ollama_base_url: str = "http://localhost:11434"
    default_ollama_model: str = "qwen2.5:0.5b"
    # Shorter generations = faster UX (raise for long answers)
    ollama_num_predict: int = 384
    # Smaller ctx = faster prompt eval on CPU; raise if answers need more history
    ollama_num_ctx: int = 2048
    # Keep model loaded between requests (Ollama JSON API). Examples: "30m", "1h", "-1" (until stop)
    ollama_keep_alive: str = "30m"
    # CPU threads for GGML (0 = Ollama default)
    ollama_num_thread: int = 0
    # Allow long first response while Ollama loads weights (CPU can exceed 10 minutes)
    ollama_request_timeout_s: float = 1800.0

    embedding_model_id: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_encode_batch_size: int = 64
    # If true, load embedding model in a background thread at startup (uses RAM; faster first RAG)
    warm_embeddings_on_startup: bool = False
    # Prime Ollama with a tiny generate so the first real user request skips model load
    warm_ollama_on_startup: bool = False
    rag_top_k: int = 4
    # Cap chars per chunk in the LLM context only (citations can still show more)
    rag_prompt_max_chars_per_chunk: int = 2200
    # Chapter / front-matter aware segmentation before token chunking
    rag_structured_segments: bool = True
    # Hybrid retrieval: dense (FAISS) + BM25 fused by RRF; optional cross-encoder rerank
    rag_hybrid_enabled: bool = True
    rag_rrf_k: int = 60
    rag_dense_candidate_mult: int = 8
    rag_bm25_top_m: int = 40
    rag_rerank_enabled: bool = False
    rag_rerank_model_id: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rag_rerank_pool: int = 24
    rag_rerank_max_chars: int = 2000
    chunk_target_tokens: int = 600
    chunk_overlap_tokens: int = 120
    context_window_tokens: int = 8192

    cors_origins: str = "http://localhost:5173,http://localhost:80,http://localhost"


settings = Settings()
