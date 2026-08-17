"""Shared pytest fixtures.

Bakes the FastEmbed Qdrant/bm25 model into a temp cache dir and points
services.common.retrieval.bm25 at it, so BM25 tests run fully offline
(no Hugging Face network access at test time). The bake itself requires
network once per test session.
"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def bm25_cache(tmp_path_factory):
    """Download Qdrant/bm25 into a session-scoped temp HF cache and wire it up.

    Downloads once per test session into pytest's tmp dir, then sets
    FASTEMBED_CACHE_PATH so services.common.retrieval.bm25 loads from it.
    """
    cache_dir = tmp_path_factory.mktemp("fastembed_cache")

    from fastembed.sparse.bm25 import Bm25

    # First call downloads into cache_dir (HF cache layout); construct once.
    Bm25(model_name="Qdrant/bm25", cache_dir=str(cache_dir), language="english")

    os.environ["FASTEMBED_CACHE_PATH"] = str(cache_dir)
    yield cache_dir
