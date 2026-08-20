"""Phase 5.0a tests — CORS middleware on retrieval_api/app.

Tests build a dedicated app with add_cors_middleware() so they are independent
of import order and of the shared `app` instance used by the rest of the suite.
"""

import os
import unittest
from unittest.mock import patch

# Must set env vars before importing app (VertexAIProvider reads at init).
os.environ["GCP_PROJECT"] = "test-project"
os.environ["MODEL_BACKEND"] = "mock"

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.retrieval_api.app import add_cors_middleware
from tests.auth_testing import auth_headers, mock_auth

_ORIGINS = "http://localhost:3000,https://iris.example.com"


def _cors_app() -> FastAPI:
    with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": _ORIGINS}):
        application = FastAPI()
        add_cors_middleware(application)
    return application


class TestCorsMiddleware(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(_cors_app())

    def _preflight(self, origin: str):
        return self.client.options(
            "/query",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-firebase-token",
            },
        )

    def test_preflight_allowlisted_origin(self):
        resp = self._preflight("http://localhost:3000")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )

    def test_preflight_covers_firebase_token_header(self):
        resp = self._preflight("https://iris.example.com")
        allowed = resp.headers.get("access-control-allow-headers", "")
        self.assertIn("x-firebase-token", allowed.lower())

    def test_preflight_unknown_origin_blocked(self):
        resp = self._preflight("http://evil.example")
        self.assertNotIn("access-control-allow-origin", resp.headers)

    def test_middleware_is_noop_without_env_var(self):
        with patch.dict(os.environ, {}, clear=True):
            application = FastAPI()
            add_cors_middleware(application)
        client = TestClient(application)
        resp = client.options(
            "/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertNotIn("access-control-allow-origin", resp.headers)


class TestCorsMiddlewareWithAuth(unittest.TestCase):
    """CORS header on a real authenticated request through the shared app."""

    @classmethod
    def setUpClass(cls):
        from services.retrieval_api.app import app as shared_app

        cls.client = TestClient(shared_app)

    def test_simple_authed_request_no_origin_no_cors_header(self):
        with mock_auth(tenant_id="tenant-a"):
            resp = self.client.post(
                "/query",
                headers=auth_headers("tenant-a"),
                json={"query": "funds", "mode": "standard"},
            )
        # Authenticated (real query against mock store); no Origin header sent
        # means the middleware adds no CORS header.
        self.assertNotEqual(resp.status_code, 401)
        self.assertNotIn("access-control-allow-origin", resp.headers)
