"""Phase 2.0 retrieval data models (Phase 4.0: request-size guards)."""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from services.common.auth.validation import (
    DOC_ID_PATTERN,
    MAX_HISTORY_TURNS,
    MAX_QUERY_CHARS,
    MAX_TOP_K_SEARCH,
    MAX_TOP_K_SYNTHESIS,
    validate_doc_ids,
    validate_history,
    validate_query,
)
from services.common.models.base import Citation


def _rethrow_as_value_error(fn, value):
    """Run a validation helper and surface its stable 422 as a Pydantic error."""
    try:
        return fn(value)
    except HTTPException as exc:
        raise ValueError(str(exc.detail)) from exc


class ActiveDoc(BaseModel):
    """A typed active document reference provided by the client."""

    ui_index: int = Field(..., ge=0)
    doc_id: str = Field(..., min_length=1, max_length=128)
    filename: str = Field(default="", max_length=255)

    @field_validator("doc_id")
    @classmethod
    def _check_doc_id(cls, value: str) -> str:
        if not isinstance(value, str) or not DOC_ID_PATTERN.match(value):
            raise ValueError("active_docs.doc_id is invalid")
        return value


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
    top_k: int = Field(default=25, ge=1, le=MAX_TOP_K_SEARCH)
    history: Optional[List[dict]] = None
    rerank_blend: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Phase 12.1: blend weight applied to the cross-encoder rerank "
                    "score against the original hybrid score. None disables reranking.",
    )
    trace: bool = Field(
        default=False,
        description="Include retrieval debug trace (HyDE, latency breakdown, chunk provenance).",
    )

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        return _rethrow_as_value_error(validate_query, value)

    @field_validator("history")
    @classmethod
    def _validate_history(cls, value):
        return _rethrow_as_value_error(validate_history, value)

    @field_validator("doc_ids")
    @classmethod
    def _validate_doc_ids(cls, value):
        return _rethrow_as_value_error(validate_doc_ids, value)


class SearchResponse(BaseModel):
    results: List[ScoredChunk]
    mode: str
    latency_ms: float
    trace: Optional[dict] = None


class QueryRequest(BaseModel):
    query: str = Field(..., max_length=MAX_QUERY_CHARS)
    mode: str = Field(default="standard", pattern="^(standard|deep)$")
    session_id: Optional[str] = None
    history: Optional[List[dict]] = None
    doc_ids: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=MAX_TOP_K_SYNTHESIS)
    trace: bool = Field(
        default=False,
        description="Include retrieval debug trace (HyDE, latency breakdown, chunk provenance).",
    )
    active_docs: Optional[List[ActiveDoc]] = Field(
        default=None,
        max_length=50,
        description="Ordered list of active documents for intent routing. "
                    '[{"ui_index": 1, "doc_id": "doc_001", "filename": "report.pdf"}]',
    )

    @field_validator("query")
    @classmethod
    def _validate_query(cls, value: str) -> str:
        return _rethrow_as_value_error(validate_query, value)

    @field_validator("history")
    @classmethod
    def _validate_history(cls, value):
        return _rethrow_as_value_error(validate_history, value)

    @field_validator("doc_ids")
    @classmethod
    def _validate_doc_ids(cls, value):
        return _rethrow_as_value_error(validate_doc_ids, value)

    @model_validator(mode="after")
    def _validate_active_docs(self):
        docs = self.active_docs
        if docs:
            doc_ids = [d.doc_id for d in docs]
            if len(set(doc_ids)) != len(doc_ids):
                raise ValueError("active_docs contains duplicate doc_id values")
            indexes = [d.ui_index for d in docs]
            if len(set(indexes)) != len(indexes):
                raise ValueError("active_docs contains duplicate ui_index values")
        return self


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    mode: str
    latency_ms: float
    chunks_used: int
    session_id: Optional[str] = None
    trace: Optional[dict] = None


class DeleteResponse(BaseModel):
    deleted_chunks: int
    resource_id: str


class SessionCreateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    document_ids: Optional[List[str]] = None

    @field_validator("document_ids")
    @classmethod
    def _validate_document_ids(cls, value):
        return _rethrow_as_value_error(validate_doc_ids, value)


class SessionResponse(BaseModel):
    session_id: str
    tenant_id: str
    name: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[dict]


class SessionMessagesResponse(BaseModel):
    messages: List[dict]


class ViewUrlResponse(BaseModel):
    url: str
    expires_in_seconds: int = 900


class DocStatusResponse(BaseModel):
    doc_id: str
    tenant_id: str
    chunks: int
    pages: int
    total_pages: Optional[int] = None
    status: str = "processing"


class UploadResponse(BaseModel):
    doc_id: str
    status: str  # "processing" | "already_ingested" | "rejected"
    detail: Optional[str] = None


class DocumentInfo(BaseModel):
    """A single document in the listing."""
    doc_id: str
    chunk_count: int
    page_count: int
    total_pages: Optional[int] = None
    status: str = "processing"


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]
