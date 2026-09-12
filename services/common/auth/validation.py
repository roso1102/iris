"""ID validation + request-size guards (Phase 4.0 / Phase 0.1).

Prevents path traversal, NoSQL injection, and malformed database keys from
reaching Qdrant / Firestore / GCS. All IDs are whitelist-regex validated
before they are concatenated into paths or filters.

Phase 0.1: request fields are validated strictly. Malformed history/doc lists
are *rejected* with a stable validation error, never silently truncated.
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
MAX_HISTORY_MESSAGE_CHARS = 4000
MAX_HISTORY_CHARS = 8000
MAX_DOC_IDS = 50
MAX_TOP_K_SYNTHESIS = 20
MAX_TOP_K_SEARCH = 50

_VALID_ROLES = ("user", "assistant")


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
    """Validate and normalize conversation history.

    Rejects (rather than truncates) malformed input: a non-list, too many
    turns, unknown roles, empty/non-string content, or oversized content.
    Returns a normalized ``[{"role", "content"}]`` list.
    """
    if history is None:
        return []
    if not isinstance(history, list):
        _reject("history must be a list")
    if len(history) > max_turns:
        _reject(f"history exceeds {max_turns} turns")
    normalized: list[dict] = []
    total_chars = 0
    for turn in history:
        if not isinstance(turn, dict):
            _reject("each history item must be an object")
        role = turn.get("role")
        if role not in _VALID_ROLES:
            _reject("history role must be 'user' or 'assistant'")
        content = turn.get("content")
        if not isinstance(content, str) or not content.strip():
            _reject("history content must be a non-empty string")
        if len(content) > MAX_HISTORY_MESSAGE_CHARS:
            _reject(
                f"history message exceeds {MAX_HISTORY_MESSAGE_CHARS} characters"
            )
        total_chars += len(content)
        if total_chars > MAX_HISTORY_CHARS:
            _reject(f"history exceeds {MAX_HISTORY_CHARS} characters in total")
        normalized.append({"role": role, "content": content})
    return normalized


def validate_doc_ids(
    doc_ids: list | None, max_ids: int = MAX_DOC_IDS
) -> list[str]:
    """Validate, de-duplicate and bound a document-id list."""
    if doc_ids is None:
        return []
    if not isinstance(doc_ids, list):
        _reject("doc_ids must be a list")
    validated: list[str] = []
    for doc_id in doc_ids:
        if not isinstance(doc_id, str):
            _reject("each doc_id must be a string")
        validate_doc_id(doc_id)
        if doc_id not in validated:
            validated.append(doc_id)
    if len(validated) > max_ids:
        _reject(f"doc_ids exceeds {max_ids} entries")
    return validated


def validate_top_k(top_k: int, for_synthesis: bool) -> int:
    cap = MAX_TOP_K_SYNTHESIS if for_synthesis else MAX_TOP_K_SEARCH
    if top_k < 1:
        _reject("top_k must be >= 1")
    return min(top_k, cap)
