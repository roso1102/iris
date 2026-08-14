"""Phase 2.0 retrieval data models."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
    query: str
    mode: str = Field(default="standard", pattern="^(standard|deep)$")
    doc_ids: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=100)
    history: Optional[List[dict]] = None


class SearchResponse(BaseModel):
    results: List[ScoredChunk]
    mode: str
    latency_ms: float


class DeleteResponse(BaseModel):
    deleted_chunks: int
    resource_id: str
