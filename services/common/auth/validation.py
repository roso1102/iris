"""ID validation + request-size guards (Phase 4.0).

Prevents path traversal, NoSQL injection, and malformed database keys from
reaching Qdrant / Firestore / GCS. All IDs are whitelist-regex validated
before they are concatenated into paths or filters.
"""

from __future__ import annotations

import re

from fastapi import HTTPException

TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
DOC_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

# Request-size / cost-abuse guards — enforced BEFORE any provider call.
MAX_QUERY_CHARS = 4000
MAX_HISTORY_TURNS = 6
MAX_TOP_K_SYNTHESIS = 20
MAX_TOP_K_SEARCH = 50


def _reject(detail: str) -> None:
    raise HTTPException(status_code=422, detail=detail)


def validate_tenant_id(tenant_id: str) -> str:
    if not tenant_id or not TENANT_ID_PATTERN.match(tenant_id):
        _reject("tenant_id contains invalid characters (allowed: [a-zA-Z0-9_-], max 64)")
    return tenant_id


def validate_doc_id(doc_id: str) -> str:
    if not doc_id or not DOC_ID_PATTERN.match(doc_id):
        _reject("doc_id contains invalid characters (allowed: [a-zA-Z0-9_-], max 128)")
    return doc_id


def validate_session_id(session_id: str) -> str:
    if not session_id or not SESSION_ID_PATTERN.match(session_id):
        _reject(
            "session_id contains invalid characters (allowed: [a-zA-Z0-9_-], max 128)"
        )
    return session_id


def validate_query(query: str) -> str:
    if not query or not query.strip():
        _reject("query must not be empty")
    if len(query) > MAX_QUERY_CHARS:
        _reject(f"query exceeds {MAX_QUERY_CHARS} characters")
    return query.strip()


def validate_history(history: list | None, max_turns: int = MAX_HISTORY_TURNS) -> list:
    """Truncate history to the sliding window instead of rejecting it."""
    if not history:
        return []
    return history[-max_turns:]


def validate_top_k(top_k: int, for_synthesis: bool) -> int:
    cap = MAX_TOP_K_SYNTHESIS if for_synthesis else MAX_TOP_K_SEARCH
    if top_k < 1:
        _reject("top_k must be >= 1")
    return min(top_k, cap)
