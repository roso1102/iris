"""Phase 2.0 retrieval data models (Phase 4.0: request-size guards)."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from services.common.auth.validation import (
    MAX_HISTORY_TURNS,
    MAX_QUERY_CHARS,
    MAX_TOP_K_SEARCH,
    MAX_TOP_K_SYNTHESIS,
)
from services.common.models.base import Citation


class ScoredChunk(BaseModel):
    """A retrieved chunk with its fusion score."""

    chunk_id: str
    doc_id: str
    tenant_id: str
    session_id: Optional[str] = None
    text: str
    bbox: List[float]
    page_number: int
    element_type: str
    source: str = "docling_text"
    score: float
    metadata: Dict[str, object] = Field(
        default_factory=dict,
        description="Extraction metadata (e.g. extraction_confidence for standard_ocr)",
    )


class SearchRequest(BaseModel):
    query: str = Field(..., max_length=MAX_QUERY_CHARS)
    mode: str = Field(default="standard", pattern="^(standard|deep)$")
    doc_ids: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=MAX_TOP_K_SEARCH)
    history: Optional[List[dict]] = None


class SearchResponse(BaseModel):
    results: List[ScoredChunk]
    mode: str
    latency_ms: float


class QueryRequest(BaseModel):
    query: str = Field(..., max_length=MAX_QUERY_CHARS)
    mode: str = Field(default="standard", pattern="^(standard|deep)$")
    session_id: Optional[str] = None
    history: Optional[List[dict]] = None
    doc_ids: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=MAX_TOP_K_SYNTHESIS)


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    mode: str
    latency_ms: float
    chunks_used: int


class DeleteResponse(BaseModel):
    deleted_chunks: int
    resource_id: str


class SessionCreateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    document_ids: Optional[List[str]] = None


class SessionResponse(BaseModel):
    session_id: str
    tenant_id: str
    name: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[dict]


class ViewUrlResponse(BaseModel):
    url: str
    expires_in_seconds: int = 900
