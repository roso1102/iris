"""Shared data model for the IRIS ingestion pipeline.

A `Chunk` is the unit everything downstream (embedding, Qdrant, retrieval,
citations) works on. Bbox is ALWAYS normalized [left, top, right, bottom]
in 0-1 page coordinates — the same convention `Citation.bbox` uses (base.py).
"""

from __future__ import annotations

import hashlib
import math
import uuid
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

# Version stamped into deterministic chunk ids so a chunker change produces
# new ids rather than colliding with older content.
CHUNKER_VERSION = "chunker-v1"

# Full-page fallback geometry: a page-level citation, never a precise box.
PAGE_LEVEL_BBOX = [0.0, 0.0, 1.0, 1.0]


def normalize_bbox(
    bbox,
    *,
    page_level: bool = False,
    source: str = "element",
    confidence: float = 1.0,
) -> tuple[list[float], bool, str, float]:
    """Validate a normalized bbox; downgrade invalid geometry to page-level.

    A valid box has four finite, normalized values with ``left < right`` and
    ``top < bottom``. Anything else is replaced with the full-page box and
    tagged ``invalid_downgraded`` so it can never be rendered as a precise
    highlight.
    """
    if isinstance(bbox, (list, tuple)) and not isinstance(bbox, (str, bytes)) and len(bbox) == 4:
        if all(
            isinstance(v, (int, float))
            and not isinstance(v, bool)
            and math.isfinite(float(v))
            for v in bbox
        ):
            left, top, right, bottom = (float(v) for v in bbox)
            if 0.0 <= left < right <= 1.0 and 0.0 <= top < bottom <= 1.0:
                return [left, top, right, bottom], bool(page_level), source, float(confidence)
    return list(PAGE_LEVEL_BBOX), True, "invalid_downgraded", 0.0


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
    page_level: Optional[bool] = None
    bbox_source: Optional[str] = None
    bbox_confidence: Optional[float] = None

    @property
    def char_count(self) -> int:
        return len(self.text.strip())


class Chunk(BaseModel):
    """A content unit ready to embed + store."""

    id: str = Field(default="")
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
    page_level: bool = False
    bbox_source: str = "element"
    bbox_confidence: float = 1.0
    metadata: Dict[str, object] = Field(
        default_factory=dict,
        description="Extraction metadata, e.g. extraction_confidence + ocr_confidence_score",
    )

    @model_validator(mode="after")
    def _ensure_deterministic_id(self):
        """Phase 0.1: chunk ids are content-addressed, so retries/redelivery
        cannot create duplicate points for the same content."""
        if not self.id:
            payload = "|".join([
                self.tenant_id,
                self.doc_id,
                str(self.page_number),
                self.element_type.value,
                ",".join(f"{float(v):.6f}" for v in self.bbox),
                self.text,
                CHUNKER_VERSION,
            ])
            # Qdrant accepts unsigned integers or canonical UUIDs as point
            # IDs. Preserve the SHA-256 content address while representing it
            # as a deterministic UUID so retries remain idempotent.
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            self.id = str(uuid.UUID(hex=digest[:32]))
        return self
