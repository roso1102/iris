"""
ModelProvider Abstract Base Class for IRIS.
All model inference calls (embeddings, VLM extraction, synthesis, SLM rewrite)
MUST inherit from and go through this interface. Direct SDK imports in application code
are strictly prohibited by SRS FR-8.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    doc_id: str
    page_number: int
    bbox: List[float] = Field(description="[left, top, right, bottom] normalized coordinates")
    text_snippet: str


class StructuredAnswer(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)


class ModelProvider(ABC):
    """Abstract Model Provider Interface."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generates a 768-dimensional vector embedding using the configured model
        (default: Vertex AI text-embedding-004).
        """
        pass

    @abstractmethod
    def extract_table(self, image_bytes: bytes) -> str:
        """
        Vision-Language Model (VLM) call on a cropped table/figure image region.
        Returns structured markdown representation of the table/figure.
        """
        pass

    @abstractmethod
    def ocr_page(self, image_bytes: bytes) -> str:
        """
        Vision-Language Model (VLM) full-page call for scanned or low-text pages (<150 chars).
        Reads rendered pixels directly, bypassing legacy font encodings (KrutiDev/DevLys).
        """
        pass

    @abstractmethod
    def synthesize(self, context: str, query: str) -> StructuredAnswer:
        """
        Generates a grounded natural language answer with structured citations.
        """
        pass

    @abstractmethod
    def rewrite_query(self, query: str, history: List[dict]) -> str:
        """
        SLM-tier query rewriter. Uses sliding window history (last N messages)
        to rewrite follow-up questions into self-contained search queries.
        """
        pass

    @abstractmethod
    def generate_hyde(self, query: str) -> str:
        """
        HyDE (Hypothetical Document Embeddings) generator for Deep Search mode.
        """
        pass
