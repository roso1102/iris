"""
Mock ModelProvider implementation for zero-cost local testing and unit tests.
"""

from typing import List, Optional
from services.common.models.base import ModelProvider, StructuredAnswer, Citation


class MockModelProvider(ModelProvider):
    """Mock implementation returning deterministic outputs for local testing."""

    def __init__(self, embed_dim: int = 3072):
        self.embed_dim = embed_dim

    def embed(self, text: str) -> List[float]:
        # Return dummy normalized vector
        return [0.1] * self.embed_dim

    def extract_table(self, image_bytes: bytes) -> str:
        return "| Column 1 | Column 2 |\n|---|\n| Mock Data 1 | Mock Data 2 |"

    def ocr_page(self, image_bytes: bytes) -> str:
        return "Mock extracted full page text content."

    def synthesize(self, context: str, query: str) -> StructuredAnswer:
        return StructuredAnswer(
            answer=f"Mock synthesis answer for query: '{query}' based on provided context.",
            citations=[
                Citation(
                    doc_id="mock_doc_1",
                    page_number=1,
                    bbox=[0.1, 0.2, 0.5, 0.4],
                    text_snippet="Mock source snippet"
                )
            ]
        )

    def rewrite_query(self, query: str, history: List[dict]) -> str:
        return f"Self-contained mock query for '{query}'"

    def generate_hyde(self, query: str) -> str:
        return f"Hypothetical answer snippet for query: '{query}'"
