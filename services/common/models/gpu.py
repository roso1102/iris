"""Self-hosted GPU model provider (Phase 10.0).

Provides local GPU inference for embeddings, VLM extraction, and synthesis
using a self-hosted model server (TGI, vLLM, or similar). Dormant for MVP;
activated by setting MODEL_BACKEND=self-hosted-gpu in Phase 10.0.

TODO (Phase 10.0):
- Implement embed() with a local text-embedding server
- Implement extract_table() and ocr_page() via GPU-accelerated VLM
- Implement synthesize(), rewrite_query(), generate_hyde()
- Wire GPU server URL/config via env vars
"""

from __future__ import annotations

from typing import List

from services.common.models.base import ModelProvider, StructuredAnswer


class SelfHostedGPUProvider(ModelProvider):
    """Dormant GPU provider stub. Implemented in Phase 10.0."""

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError(
            "Self-hosted GPU embeddings not implemented. See Phase 10.0."
        )

    def extract_table(self, image_bytes: bytes) -> str:
        raise NotImplementedError(
            "Self-hosted GPU table extraction not implemented. See Phase 10.0."
        )

    def ocr_page(self, image_bytes: bytes) -> str:
        raise NotImplementedError(
            "Self-hosted GPU OCR not implemented. See Phase 10.0."
        )

    def synthesize(self, context: str, query: str) -> StructuredAnswer:
        raise NotImplementedError(
            "Self-hosted GPU synthesis not implemented. See Phase 10.0."
        )

    def rewrite_query(self, query: str, history: List[dict]) -> str:
        raise NotImplementedError(
            "Self-hosted GPU query rewrite not implemented. See Phase 10.0."
        )

    def generate_hyde(self, query: str) -> str:
        raise NotImplementedError(
            "Self-hosted GPU HyDE not implemented. See Phase 10.0."
        )
