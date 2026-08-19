"""Shared test helper for Phase 4.0 auth (local component tests).

Patches `services.common.auth.jwt.verify_firebase_token` so FastAPI TestClient
tests can exercise the full endpoint path (auth dependency -> tenant rewrite)
without touching Firebase. Deterministic, zero-cost, no network.

Usage:
    with mock_auth(tenant_id="tenant-a", role="member"):
        resp = client.post("/search", headers={"authorization": "Bearer <anything>"})
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from services.common.auth.jwt import AuthContext


@contextmanager
def mock_auth(tenant_id: str = "tenant-a", role: str = "member", uid: str = "test-user"):
    """Patch the JWT verifier to return a fixed AuthContext.

    The token string itself is ignored by the mock; the endpoint receives the
    `authorization` header but the verifier returns the configured claims.
    """
    with patch(
        "services.common.auth.jwt.verify_firebase_token",
        return_value={
            "uid": uid,
            "tenant_id": tenant_id,
            "role": role,
        },
    ) as mock_verify:
        mock_verify.return_value = {
            "uid": uid,
            "tenant_id": tenant_id,
            "role": role,
        }
        yield mock_verify


def auth_headers(tenant_id: str = "tenant-a", role: str = "member") -> dict:
    """Headers for a request whose token maps to the given claims (mock-active)."""
    return {"Authorization": f"Bearer token-{tenant_id}-{role}"}
