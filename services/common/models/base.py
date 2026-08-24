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
    chunk_id: str = ""
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

    def embed_query(self, text: str) -> List[float]:
        """
        Query-side embedding. text-embedding-004 is trained asymmetrically:
        retrieval queries must be embedded with task_type RETRIEVAL_QUERY to
        match documents embedded with RETRIEVAL_DOCUMENT — using the document
        task for both sides measurably degrades ranking. Providers that don't
        distinguish sides (mock/gpu) inherit this embed() delegation.
        """
        return self.embed(text)

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
    def synthesize(
        self,
        context: str,
        query: str,
        source_chunks: List[dict],
    ) -> StructuredAnswer:
        """
        Generates a grounded natural language answer with structured citations.

        `source_chunks` is a list of dicts, each describing one retrieved chunk:
        {"chunk_id": str, "doc_id": str, "page_number": int, "bbox": [l,t,r,b],
         "text": str}. Citations emitted by the provider must reference one of
        these chunk_ids so the caller can validate grounding.
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

    @abstractmethod
    def rerank(
        self, query: str, passages: List[str]
    ) -> List[float]:
        """
        Cross-encoder reranking (Phase 12.1): score a list of passages against
        the query and return one relevance score per passage (higher = more
        relevant), in the SAME order as `passages`.

        Backed by the Vertex AI Ranking API (semantic-ranker) via MODEL_BACKEND.
        The returned scores are converted to ranks and fused with the hybrid
        RRF scores (weight `blend`), NOT blended raw — see
        `services.common.retrieval.rrf.fuse_rerank_scores`.
        """
        pass

    @abstractmethod
    def generate_cross_lingual_variants(
        self,
        query: str,
        num_variants: int = 1,
    ) -> List[str]:
        """Generate Hindi (Devanagari) search query variants.

        Translates Latin-script queries into Hindi and transliterates
        romanized Hindi into Devanagari. Returns empty list on failure
        (caller falls back to original-only search).
        """
        pass
