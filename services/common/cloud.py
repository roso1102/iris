"""Native client timeouts + transient-only retries for cloud services.

Firestore, GCS and Pub/Sub all expose transport-level ``timeout`` parameters,
so they are bounded here at the transport boundary and retried only on
transient failures. Process isolation is deliberately NOT used for these calls
— it is reserved for Vertex SDK operations that have no native deadline (see
``services.common.reliability.run_with_timeout``).
"""

from __future__ import annotations

import os
from typing import Any, Callable, TypeVar

from services.common.reliability import RetryPolicy, retry_call

T = TypeVar("T")


def _env_seconds(name: str, default: float) -> float:
    try:
        return max(0.001, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


FIRESTORE_TIMEOUT_SECONDS = _env_seconds("FIRESTORE_TIMEOUT_SECONDS", 10.0)
GCS_TIMEOUT_SECONDS = _env_seconds("GCS_TIMEOUT_SECONDS", 30.0)
PUBSUB_TIMEOUT_SECONDS = _env_seconds("PUBSUB_TIMEOUT_SECONDS", 30.0)

# Registry asserted by tests: every cloud dependency has a configured deadline.
NATIVE_TIMEOUTS = {
    "firestore": FIRESTORE_TIMEOUT_SECONDS,
    "gcs": GCS_TIMEOUT_SECONDS,
    "pubsub": PUBSUB_TIMEOUT_SECONDS,
}

FIRESTORE_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=0.2,
    max_delay=2.0,
    per_attempt_timeout=FIRESTORE_TIMEOUT_SECONDS,
    overall_deadline=30.0,
    operation="firestore",
)
GCS_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=0.2,
    max_delay=2.0,
    per_attempt_timeout=GCS_TIMEOUT_SECONDS,
    overall_deadline=90.0,
    operation="gcs",
)
PUBSUB_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=0.2,
    max_delay=2.0,
    per_attempt_timeout=PUBSUB_TIMEOUT_SECONDS,
    overall_deadline=60.0,
    operation="pubsub",
)


def _call(fn: Callable[[], T], policy: RetryPolicy) -> T:
    """Retry a call whose transport timeout is already applied natively."""
    return retry_call(fn, policy, isolate=False)


def fs_get(ref, **kwargs) -> Any:
    return _call(
        lambda: ref.get(timeout=FIRESTORE_TIMEOUT_SECONDS, **kwargs), FIRESTORE_POLICY
    )


def fs_set(ref, data, **kwargs) -> Any:
    return _call(
        lambda: ref.set(data, timeout=FIRESTORE_TIMEOUT_SECONDS, **kwargs),
        FIRESTORE_POLICY,
    )


def fs_delete(ref, **kwargs) -> Any:
    return _call(
        lambda: ref.delete(timeout=FIRESTORE_TIMEOUT_SECONDS, **kwargs), FIRESTORE_POLICY
    )


def fs_update(ref, data, **kwargs) -> Any:
    return _call(
        lambda: ref.update(data, timeout=FIRESTORE_TIMEOUT_SECONDS, **kwargs),
        FIRESTORE_POLICY,
    )


def fs_get_all(query, **kwargs) -> list:
    return _call(
        lambda: list(query.get(timeout=FIRESTORE_TIMEOUT_SECONDS, **kwargs)),
        FIRESTORE_POLICY,
    )


def fs_stream(query, **kwargs) -> list:
    return _call(
        lambda: list(query.stream(timeout=FIRESTORE_TIMEOUT_SECONDS, **kwargs)),
        FIRESTORE_POLICY,
    )


def gcs_exists(blob) -> bool:
    return _call(lambda: blob.exists(timeout=GCS_TIMEOUT_SECONDS), GCS_POLICY)


def gcs_download(blob, filename) -> Any:
    return _call(
        lambda: blob.download_to_filename(filename, timeout=GCS_TIMEOUT_SECONDS),
        GCS_POLICY,
    )


def gcs_upload(blob, filename, **kwargs) -> Any:
    return _call(
        lambda: blob.upload_from_filename(
            filename, timeout=GCS_TIMEOUT_SECONDS, **kwargs
        ),
        GCS_POLICY,
    )


def gcs_delete(blob) -> Any:
    return _call(lambda: blob.delete(timeout=GCS_TIMEOUT_SECONDS), GCS_POLICY)


def pubsub_publish(publisher, topic: str, data: bytes, **attributes) -> Any:
    """Publish with a native RPC timeout; returns the result (blocking)."""
    def _do():
        future = publisher.publish(
            topic, data, timeout=PUBSUB_TIMEOUT_SECONDS, **attributes
        )
        return future.result(timeout=PUBSUB_TIMEOUT_SECONDS)

    return _call(_do, PUBSUB_POLICY)


def pubsub_publish_future(publisher, topic: str, data: bytes, **attributes) -> Any:
    """Publish with a native RPC timeout; returns the future for concurrent waits.

    Only the synchronous ``publish`` call is retried (transient failures); the
    returned future is awaited by the caller under its own overall deadline.
    """
    return _call(
        lambda: publisher.publish(
            topic, data, timeout=PUBSUB_TIMEOUT_SECONDS, **attributes
        ),
        PUBSUB_POLICY,
    )
