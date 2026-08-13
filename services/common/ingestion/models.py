"""Shared data model for the IRIS ingestion pipeline.

A `Chunk` is the unit everything downstream (embedding, Qdrant, retrieval,
citations) works on. Bbox is ALWAYS normalized [left, top, right, bottom]
in 0-1 page coordinates — the same convention `Citation.bbox` uses (base.py).
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    """Docling element labels, normalized for the pipeline."""

    TEXT = "Text"
    TABLE = "Table"
    PICTURE = "Picture"
    CAPTION = "Caption"
    TITLE = "Title"
    LIST_ITEM = "ListItem"
    PAGE_HEADER = "PageHeader"
    PAGE_FOOTER = "PageFooter"
    OTHER = "Other"


class RouteDecision(str, Enum):
    """Page-Wise VLM Router outcome for a single element."""

    DOCLING_TEXT = "docling_text"      # zero API cost
    VLM_TABLE = "vlm_table"            # Gemini Vision on cropped table bbox
    VLM_PICTURE = "vlm_picture"        # Gemini Vision on cropped figure bbox
    VLM_FULL_PAGE = "vlm_full_page"    # Gemini Vision on full page crop


class ParsedElement(BaseModel):
    """One element extracted by Docling, normalized for the router."""

    page_number: int = Field(ge=1, description="1-based page number")
    element_type: ElementType
    text: str = ""
    bbox: List[float] = Field(
        description="Normalized [left, top, right, bottom] in 0-1 page coords"
    )

    @property
    def char_count(self) -> int:
        return len(self.text.strip())


class Chunk(BaseModel):
    """A content unit ready to embed + store."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    doc_id: str
    session_id: Optional[str] = None
    page_number: int = Field(ge=1)
    element_type: ElementType
    text: str
    bbox: List[float] = Field(
        description="Normalized [left, top, right, bottom] in 0-1 page coords"
    )
    source: RouteDecision = RouteDecision.DOCLING_TEXT
    embedding: Optional[List[float]] = None
