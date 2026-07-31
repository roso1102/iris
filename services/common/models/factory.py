"""
ModelProvider Factory for IRIS.
Reads MODEL_BACKEND env var from Secret Manager / Environment to instantiate provider.
"""

import os
from services.common.models.base import ModelProvider
from services.common.models.mock import MockModelProvider
from services.common.models.vertex import VertexAIProvider


def get_model_provider() -> ModelProvider:
    """
    Factory function returning the active ModelProvider instance.
    MODEL_BACKEND options: 'vertex' (default), 'mock' (local dev/test).
    """
    backend = os.getenv("MODEL_BACKEND", "vertex").lower()
    
    if backend == "vertex":
        return VertexAIProvider()
    elif backend == "mock":
        return MockModelProvider()
    else:
        raise ValueError(f"Unsupported MODEL_BACKEND: '{backend}'. Options: 'vertex', 'mock'.")
