"""Firebase JWT verification + FastAPI auth dependency (Phase 4.0).

The verified JWT is the ONLY source of truth for `tenant_id`. Client-supplied
tenant values (headers, bodies, paths) are never trusted — the auth layer
derives the tenant exclusively from the token's custom claims.

Per-route usage only. NEVER apply this as global middleware: the
ingestion-worker Pub/Sub push endpoints receive Google Cloud OIDC tokens
(machine-to-machine), not Firebase user JWTs, and must stay on Cloud Run IAM.

FastAPI is imported guardedly so the Flask-based ingestion-worker can import
the shared verifier without FastAPI installed. When FastAPI is unavailable
(worker), `require_auth` is never invoked.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:  # FastAPI present in retrieval-api; absent in Flask-based ingestion-worker.
    from fastapi import Header, HTTPException
except ImportError:  # pragma: no cover - worker container
    Header = None
    HTTPException = None

# FastAPI dependency-injection defaults. Evaluated at def time, so guard each:
# with FastAPI the Header fields make FastAPI inject the relevant headers; without
# it, a plain string keeps the module import-safe (never used in the worker).
_AUTH_HEADER_DEFAULT = Header(default="") if Header is not None else ""
_FIREBASE_HEADER_DEFAULT = Header(default="") if Header is not None else ""

# Lazily-initialized firebase_admin app (avoids touching ADC at import time,
# which keeps the local test suite and non-auth code paths import-safe).
_APP = None


class AuthError(Exception):
    """Base class for auth failures mapped to HTTP status codes."""


class MissingTokenError(AuthError):
    pass


class InvalidTokenError(AuthError):
    pass


class MissingTenantClaimError(AuthError):
    pass


@dataclass(frozen=True)
class AuthContext:
    """Verified caller identity, extracted from the Firebase JWT."""

    uid: str
    tenant_id: str
    role: str = "member"


def _get_app():
    global _APP
    if _APP is None:
        import firebase_admin
        from firebase_admin import credentials

        _APP = firebase_admin.initialize_app(
            credentials.ApplicationDefault(), name="[DEFAULT]"
        )
    return _APP


def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return its claims.

    Raises:
        MissingTokenError: empty/malformed token.
        InvalidTokenError: expired, revoked, or unverifiable token.
    """
    if not token or not token.strip():
        raise MissingTokenError("Missing bearer token")

    from firebase_admin import auth as firebase_auth

    try:
        return firebase_auth.verify_id_token(token.strip(), app=_get_app())
    except AuthError:
        raise
    except Exception as exc:  # firebase raises ValueError / InvalidIdTokenError etc.
        raise InvalidTokenError(f"Invalid or expired token: {exc}") from exc


def token_to_auth_context(claims: dict) -> AuthContext:
    """Build an AuthContext from verified claims.

    Raises:
        MissingTenantClaimError: the token carries no `tenant_id` custom claim.
    """
    uid = str(claims.get("uid", ""))
    tenant_id = str(claims.get("tenant_id", "") or "").strip()
    if not tenant_id:
        raise MissingTenantClaimError(
            "Token has no tenant_id claim; user is not provisioned for a tenant"
        )
    role = str(claims.get("role", "member") or "member").strip() or "member"
    return AuthContext(uid=uid, tenant_id=tenant_id, role=role)


def require_auth(
    authorization: str = _AUTH_HEADER_DEFAULT,
    x_firebase_token: str = _FIREBASE_HEADER_DEFAULT,
) -> "AuthContext":
    """FastAPI dependency: verify the Firebase ID token and return AuthContext.

    The token is read from `X-Firebase-Token` first, falling back to the
    standard `Authorization: Bearer` header. The custom header lets Cloud Run
    pass Firebase user ID tokens through — Cloud Run's platform validates any
    `Authorization: Bearer` token it sees as a Google OIDC token, and a
    Firebase user JWT would be rejected there before reaching the app.

    - Missing/malformed/expired token  -> 401 Unauthorized.
    - Valid token missing tenant_id     -> 403 Forbidden.
    """
    if HTTPException is None:  # pragma: no cover - never invoked in worker
        raise RuntimeError("require_auth requires FastAPI")

    token = (x_firebase_token or "").strip()
    if not token:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        claims = verify_firebase_token(token)
        return token_to_auth_context(claims)
    except MissingTenantClaimError as exc:
        logger.warning("Auth denied: %s", exc)
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
