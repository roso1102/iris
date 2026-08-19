"""Phase 4.0 tests — per-tenant rate limiting."""

import os
import unittest
from unittest.mock import patch

os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi.testclient import TestClient

from tests.auth_testing import auth_headers, mock_auth

from services.common.auth.rate_limit import FixedWindowRateLimiter, limiter
from services.common.ingestion.models import Chunk, ElementType, RouteDecision
from services.retrieval_api.app import app, store


def _chunk(tenant_id: str, doc_id: str, text: str) -> Chunk:
    return Chunk(
        tenant_id=tenant_id,
        doc_id=doc_id,
        page_number=1,
        element_type=ElementType.TEXT,
        text=text,
        bbox=[0.1, 0.1, 0.5, 0.4],
        source=RouteDecision.DOCLING_TEXT,
        embedding=[0.1] * 768,
    )


class TestFixedWindowRateLimiter(unittest.TestCase):

    def setUp(self):
        self.limiter = FixedWindowRateLimiter(limit=2)

    def test_under_limit_ok(self):
        self.limiter.check("tenant:t1")
        self.limiter.check("tenant:t1")
        # no exception raised

    def test_over_limit_429(self):
        from fastapi import HTTPException

        self.limiter.check("tenant:t1")
        self.limiter.check("tenant:t1")
        with self.assertRaises(HTTPException) as ctx:
            self.limiter.check("tenant:t1")
        self.assertEqual(ctx.exception.status_code, 429)

    def test_keyed_per_tenant(self):
        self.limiter.check("tenant:t1")
        self.limiter.check("tenant:t1")
        # Different tenant still allowed.
        self.limiter.check("tenant:t2")

    def test_reset(self):
        self.limiter.check("tenant:t1")
        self.limiter.check("tenant:t1")
        self.limiter.reset()
        self.limiter.check("tenant:t1")


class TestRateLimitEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self._gcs = patch(
            "services.retrieval_api.app._get_gcs_client", return_value=None
        )
        self._fs = patch(
            "services.retrieval_api.app._get_firestore_client", return_value=None
        )
        self._gcs.start()
        self._fs.start()
        store._by_doc.clear()
        limiter.reset()
        self._orig_limit = limiter.limit
        limiter.limit = 2

    def tearDown(self):
        limiter.limit = self._orig_limit
        limiter.reset()
        self._gcs.stop()
        self._fs.stop()

    def test_query_429_after_limit(self):
        store.upsert_batch([_chunk("tenant-a", "d1", "government funds committee provides funding")])
        with mock_auth(tenant_id="tenant-a"):
            for _ in range(2):
                resp = self.client.post(
                    "/query",
                    json={"query": "government funds", "mode": "standard"},
                    headers=auth_headers(),
                )
                self.assertEqual(resp.status_code, 200)
            resp = self.client.post(
                "/query",
                json={"query": "government funds", "mode": "standard"},
                headers=auth_headers(),
            )
            self.assertEqual(resp.status_code, 429)

    def test_rate_limit_ignores_livez(self):
        resp = self.client.get("/livez")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
