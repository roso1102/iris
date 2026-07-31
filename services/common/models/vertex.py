"""
VertexAIProvider wrapping Google Cloud Vertex AI SDK.
Uses text-embedding-004 (3072-d) and Gemini Flash models.
"""

import os
from typing import List, Optional
from services.common.models.base import ModelProvider, StructuredAnswer, Citation


class VertexAIProvider(ModelProvider):
    """
    Production Vertex AI implementation for GCP Cloud Run.
    Model versions configured via environment variables.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        synthesis_model: str = "gemini-flash",
        lite_model: str = "gemini-flash-lite",
        embedding_model: str = "text-embedding-004",
    ):
        self.project_id = project_id or os.getenv("GCP_PROJECT", "iris-rag-prod")
        self.location = location
        self.synthesis_model_name = os.getenv("SYNTHESIS_MODEL", synthesis_model)
        self.lite_model_name = os.getenv("LITE_MODEL", lite_model)
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", embedding_model)
        self._initialized = False

    def _ensure_init(self):
        if not self._initialized:
            import vertexai
            vertexai.init(project=self.project_id, location=self.location)
            self._initialized = True

    def embed(self, text: str) -> List[float]:
        self._ensure_init()
        from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
        
        model = TextEmbeddingModel.from_pretrained(self.embedding_model_name)
        inputs = [TextEmbeddingInput(text=text, task_type="RETRIEVAL_DOCUMENT")]
        kwargs = {"output_dimensionality": 3072} if "004" in self.embedding_model_name else {}
        embeddings = model.get_embeddings(inputs, **kwargs)
        return embeddings[0].values

    def extract_table(self, image_bytes: bytes) -> str:
        self._ensure_init()
        from vertexai.generative_models import GenerativeModel, Part
        
        model = GenerativeModel(self.synthesis_model_name)
        prompt = "Extract all tables and figures from this image region into clean Markdown format."
        image_part = Part.from_data(data=image_bytes, mime_type="image/png")
        response = model.generate_content([prompt, image_part])
        return response.text

    def ocr_page(self, image_bytes: bytes) -> str:
        self._ensure_init()
        from vertexai.generative_models import GenerativeModel, Part
        
        model = GenerativeModel(self.synthesis_model_name)
        prompt = "Read all text on this page image accurately, preserving layout structure."
        image_part = Part.from_data(data=image_bytes, mime_type="image/png")
        response = model.generate_content([prompt, image_part])
        return response.text

    def synthesize(self, context: str, query: str) -> StructuredAnswer:
        self._ensure_init()
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel(self.synthesis_model_name)
        prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nSynthesize a grounded answer with citations."
        response = model.generate_content(prompt)
        # Note: In production Phase 3.0, structured Pydantic schema parsing is applied here
        return StructuredAnswer(
            answer=response.text,
            citations=[]
        )

    def rewrite_query(self, query: str, history: List[dict]) -> str:
        self._ensure_init()
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel(self.lite_model_name)
        prompt = f"Chat History:\n{history}\n\nFollow-up question: {query}\n\nRewrite as a standalone query."
        response = model.generate_content(prompt)
        return response.text.strip()

    def generate_hyde(self, query: str) -> str:
        self._ensure_init()
        from vertexai.generative_models import GenerativeModel
        
        model = GenerativeModel(self.lite_model_name)
        prompt = f"Write a hypothetical paragraph that directly answers this question: '{query}'"
        response = model.generate_content(prompt)
        return response.text.strip()
