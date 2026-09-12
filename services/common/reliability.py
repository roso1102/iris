"""Bounded retry / timeout policy shared by provider and HTTP calls (Phase 0.1).

Guarantees:

* typed transient vs permanent classification — only transient failures retry;
* connect, per-attempt and overall deadlines;
* exponential backoff with *full jitter* and ``Retry-After`` support;
* no fixed multi-second sleeps inside request handling.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import multiprocessing
import os
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Statuses that are safe to retry (REL-001 / temp.md 0.1.7).
TRANSIENT_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

_TRANSIENT_NAME_HINTS = (
    "timeout",
    "timedout",
    "unavailable",
    "resourceexhausted",
    "deadlineexceeded",
    "internalserver",
    "connectionreset",
    "connectionerror",
    "connectionaborted",
    "serviceunavailable",
)

# Deadline isolation. A timed-out blocking call runs in a forked child process
# that is hard-killed when the deadline passes, so a hung provider call can
# never permanently occupy a shared worker. ``fork`` is unavailable on Windows
# (local dev/tests); there we fall back to a thread pool, which bounds the
# caller but cannot cancel the running call.
_FORK_AVAILABLE = "fork" in multiprocessing.get_all_start_methods()

_DEADLINE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="iris-deadline"
)


class TransientError(Exception):
    """Failure that is safe to retry."""


class PermanentError(Exception):
    """Failure that must never be retried."""


class CallTimeout(TransientError):
    """A single attempt exceeded its per-attempt / transport deadline."""


def _isolated_entry(conn, fn: Callable[[], Any]) -> None:
    """Child-process entry: run ``fn`` once and send back a picklable outcome."""
    # A fork can inherit a logging lock held by another thread; replace it so
    # the child cannot deadlock on its first log record.
    try:
        logging._lock = threading.RLock()  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - defensive
        pass
    try:
        status, payload = "ok", fn()
    except BaseException as exc:  # noqa: BLE001 - relayed to the parent
        status, payload = "error", exc
    try:
        conn.send((status, payload))
    except Exception as exc:  # outcome was not picklable
        try:
            conn.send(("error", TransientError(f"unpicklable outcome: {exc}")))
        except Exception:  # pragma: no cover - defensive
            pass
    finally:
        conn.close()
        os._exit(0)


def _run_isolated(fn: Callable[[], T], timeout: float, operation: str) -> T:
    """Run ``fn`` in a forked child and hard-kill it past the deadline."""
    ctx = multiprocessing.get_context("fork")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_isolated_entry, args=(child_conn, fn), daemon=True)
    proc.start()
    child_conn.close()
    try:
        if not parent_conn.poll(timeout):
            raise CallTimeout(f"{operation}: per-attempt timeout after {timeout:g}s")
        try:
            status, payload = parent_conn.recv()
        except EOFError as exc:
            raise TransientError(f"{operation}: worker exited before returning") from exc
        if status == "ok":
            return payload
        raise payload
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join(timeout=5)
        parent_conn.close()


def _run_threaded(fn: Callable[[], T], timeout: float, operation: str) -> T:
    """Fallback used where ``fork`` is unavailable (Windows dev/tests)."""
    future = _DEADLINE_EXECUTOR.submit(fn)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise CallTimeout(f"{operation}: per-attempt timeout after {timeout:g}s") from exc


def run_with_timeout(
    fn: Callable[[], T],
    timeout: Optional[float],
    operation: str = "operation",
    isolate: Optional[bool] = None,
) -> T:
    """Run ``fn`` with a real wall-clock deadline.

    The pinned Vertex SDK (1.163.0) does not expose a transport timeout on
    ``generate_content``/``get_embeddings``, so blocking calls are bounded here
    instead. When ``isolate`` is true (the default where ``fork`` exists), the
    call runs in a child process that is killed on deadline, so a hung provider
    call cannot occupy a shared worker. Set ``isolate=False`` to force the
    thread fallback (used by tests that rely on shared in-process state).
    """
    if not timeout or timeout <= 0:
        return fn()
    use_process = _FORK_AVAILABLE if isolate is None else (isolate and _FORK_AVAILABLE)
    if use_process:
        return _run_isolated(fn, timeout, operation)
    return _run_threaded(fn, timeout, operation)


async def run_async_with_timeout(
    fn: Callable[[], Any], timeout: Optional[float], operation: str = "operation"
) -> Any:
    """Await an async callable with a real deadline."""
    if not timeout or timeout <= 0:
        return await fn()
    try:
        return await asyncio.wait_for(fn(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        raise CallTimeout(f"{operation}: per-attempt timeout after {timeout:g}s") from exc


def is_transient_status(status: int) -> bool:
    return status in TRANSIENT_STATUSES


def classify_exception(exc: BaseException) -> str:
    """Return ``"transient"`` or ``"permanent"`` for an exception."""
    if isinstance(exc, PermanentError):
        return "permanent"
    if isinstance(exc, TransientError):
        return "transient"
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError, OSError)):
        return "transient"

    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    if isinstance(status, int) and status in TRANSIENT_STATUSES:
        return "transient"

    name = type(exc).__name__.lower()
    if any(hint in name for hint in _TRANSIENT_NAME_HINTS):
        return "transient"
    return "permanent"


def retry_after_from_headers(headers: Any) -> Optional[float]:
    """Parse a numeric ``Retry-After`` (seconds) from a mapping, if present."""
    try:
        raw = headers.get("Retry-After") if headers is not None else None
    except Exception:  # pragma: no cover - defensive
        return None
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class RetryPolicy:
    """Immutable retry/timeout policy for one logical operation."""

    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0
    connect_timeout: float = 5.0
    per_attempt_timeout: float = 30.0
    overall_deadline: float = 60.0
    operation: str = "operation"

    def delay_for(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Full-jitter delay before retrying attempt index ``attempt`` (0-based)."""
        if retry_after is not None:
            return max(0.0, min(float(retry_after), self.max_delay))
        ceiling = min(self.max_delay, self.base_delay * (2 ** attempt))
        return random.uniform(0.0, ceiling)


def _deadline_expired(started: float, policy: RetryPolicy, clock: Callable[[], float]) -> bool:
    return (clock() - started) >= policy.overall_deadline


def retry_call(
    fn: Callable[[], T],
    policy: RetryPolicy,
    *,
    retry_on: Optional[Callable[[BaseException], bool]] = None,
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
    retry_after: Optional[float] = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    enforce_attempt_timeout: bool = True,
    isolate: Optional[bool] = None,
) -> T:
    """Execute ``fn`` with bounded retries. Raises the last exception on exhaustion.

    When ``enforce_attempt_timeout`` is set (default), each attempt is bounded
    by ``policy.per_attempt_timeout`` so a blocking call cannot overrun the
    deadline. ``isolate`` selects the execution mode of that bound (see
    :func:`run_with_timeout`); the default runs each attempt in a killable
    child process where ``fork`` is available.
    """
    started = clock()
    last_exc: Optional[BaseException] = None
    attempt_timeout = policy.per_attempt_timeout if enforce_attempt_timeout else None
    for attempt in range(policy.max_attempts):
        if _deadline_expired(started, policy, clock):
            if last_exc is not None:
                raise last_exc
            raise TransientError(f"{policy.operation}: overall deadline exceeded")
        try:
            return run_with_timeout(fn, attempt_timeout, policy.operation, isolate)
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:  # noqa: BLE001 - classification decides
            last_exc = exc
            is_transient = retry_on(exc) if retry_on is not None else classify_exception(exc) == "transient"
            if not is_transient or attempt >= policy.max_attempts - 1:
                raise
            if _deadline_expired(started, policy, clock):
                raise
            delay = policy.delay_for(attempt, retry_after)
            logger.warning(
                "retry operation=%s attempt=%d delay_ms=%.0f transient=true",
                policy.operation, attempt + 1, delay * 1000.0,
            )
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            sleep(delay)
    if last_exc is not None:  # pragma: no cover - loop always raises
        raise last_exc
    raise TransientError(f"{policy.operation}: retry loop exhausted")


async def retry_call_async(
    fn: Callable[[], Any],
    policy: RetryPolicy,
    *,
    retry_on: Optional[Callable[[BaseException], bool]] = None,
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
    retry_after: Optional[float] = None,
    clock: Callable[[], float] = time.monotonic,
    enforce_attempt_timeout: bool = True,
) -> Any:
    """Async variant of :func:`retry_call` using ``asyncio.sleep``.

    Each attempt is wrapped in ``asyncio.wait_for`` so a slow await is actually
    cancelled when it exceeds ``policy.per_attempt_timeout``.
    """
    started = clock()
    last_exc: Optional[BaseException] = None
    attempt_timeout = policy.per_attempt_timeout if enforce_attempt_timeout else None
    for attempt in range(policy.max_attempts):
        if _deadline_expired(started, policy, clock):
            if last_exc is not None:
                raise last_exc
            raise TransientError(f"{policy.operation}: overall deadline exceeded")
        try:
            return await run_async_with_timeout(fn, attempt_timeout, policy.operation)
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:  # noqa: BLE001
            last_exc = exc
            is_transient = retry_on(exc) if retry_on is not None else classify_exception(exc) == "transient"
            if not is_transient or attempt >= policy.max_attempts - 1:
                raise
            if _deadline_expired(started, policy, clock):
                raise
            delay = policy.delay_for(attempt, retry_after)
            logger.warning(
                "retry operation=%s attempt=%d delay_ms=%.0f transient=true",
                policy.operation, attempt + 1, delay * 1000.0,
            )
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            await asyncio.sleep(delay)
    if last_exc is not None:  # pragma: no cover
        raise last_exc
    raise TransientError(f"{policy.operation}: retry loop exhausted")
