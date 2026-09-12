"""Shared pytest configuration.

The test suite is fully offline and hermetic: BM25 uses the deterministic
in-process tokenizer selected by ``IRIS_BM25_OFFLINE`` instead of downloading
the Qdrant/bm25 model from Hugging Face. No network, cloud credentials, or
model downloads are required to run unit/component tests.

Live-provider tests (`tests/test_vertex_live.py`, `tests/test_qdrant_live.py`)
are excluded by their `live` marker and must be selected explicitly.
"""

import os

# Set before anything imports services.common.retrieval.bm25.
os.environ.setdefault("IRIS_BM25_OFFLINE", "1")

# The unit suite asserts on SDK call arguments recorded in-process; a forked
# child would not record them. Dedicated isolation tests pass isolate=True.
os.environ.setdefault("IRIS_PROCESS_ISOLATION", "0")
