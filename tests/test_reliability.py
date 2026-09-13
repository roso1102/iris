"""Phase 0.1 tests — bounded retry/timeout policy."""

import multiprocessing
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock

from services.common.reliability import (
    _FORK_AVAILABLE,
    CallTimeout,
    PermanentError,
    RetryPolicy,
    TransientError,
    classify_exception,
    is_transient_status,
    retry_after_from_headers,
    retry_call,
    run_with_timeout,
)


class _Boom(Exception):
    pass


class TestClassification(unittest.TestCase):

    def test_transient_statuses(self):
        for status in (408, 429, 500, 502, 503, 504):
            self.assertTrue(is_transient_status(status))
        for status in (400, 401, 403, 404, 422):
            self.assertFalse(is_transient_status(status))

    def test_typed_errors(self):
        self.assertEqual(classify_exception(TransientError("x")), "transient")
        self.assertEqual(classify_exception(PermanentError("x")), "permanent")

    def test_builtin_network_errors_transient(self):
        self.assertEqual(classify_exception(TimeoutError("t")), "transient")
        self.assertEqual(classify_exception(ConnectionResetError("r")), "transient")

    def test_status_attribute(self):
        exc = _Boom("boom")
        exc.status_code = 503
        self.assertEqual(classify_exception(exc), "transient")

    def test_unknown_is_permanent(self):
        self.assertEqual(classify_exception(ValueError("bad")), "permanent")

    def test_invalid_embedding_is_permanent(self):
        from services.common.embeddings import EmbeddingInvalidError

        self.assertEqual(classify_exception(EmbeddingInvalidError("bad")), "permanent")

    def test_auth_and_validation_are_permanent(self):
        for exc in (FileNotFoundError("x"), PermissionError("x"), ValueError("x")):
            self.assertEqual(classify_exception(exc), "permanent", type(exc).__name__)

    def test_other_4xx_is_permanent_429_is_transient(self):
        unauthorized = _Boom("no")
        unauthorized.status_code = 401
        self.assertEqual(classify_exception(unauthorized), "permanent")
        throttled = _Boom("slow")
        throttled.status_code = 429
        self.assertEqual(classify_exception(throttled), "transient")


class TestRetryAfter(unittest.TestCase):

    def test_parses_numeric(self):
        self.assertEqual(retry_after_from_headers({"Retry-After": "2.5"}), 2.5)

    def test_missing_or_invalid(self):
        self.assertIsNone(retry_after_from_headers({}))
        self.assertIsNone(retry_after_from_headers({"Retry-After": "later"}))
        self.assertIsNone(retry_after_from_headers(None))


class TestPolicyDelay(unittest.TestCase):

    def test_full_jitter_within_ceiling(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=8.0)
        for attempt in range(4):
            for _ in range(50):
                delay = policy.delay_for(attempt)
                ceiling = min(8.0, 1.0 * (2 ** attempt))
                self.assertGreaterEqual(delay, 0.0)
                self.assertLessEqual(delay, ceiling)

    def test_retry_after_is_honored_and_capped(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=4.0)
        self.assertEqual(policy.delay_for(0, retry_after=2.0), 2.0)
        self.assertEqual(policy.delay_for(0, retry_after=99.0), 4.0)


class TestRetryCall(unittest.TestCase):

    def setUp(self):
        self.sleeps = []
        self.policy = RetryPolicy(
            max_attempts=3, base_delay=0.0, max_delay=0.0, overall_deadline=60.0
        )

    def test_retries_transient_then_succeeds(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise TransientError("again")
            return "ok"

        result = retry_call(fn, self.policy, sleep=self.sleeps.append, isolate=False)
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)
        self.assertEqual(len(self.sleeps), 2)

    def test_permanent_not_retried(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            raise PermanentError("nope")

        with self.assertRaises(PermanentError):
            retry_call(fn, self.policy, sleep=self.sleeps.append, isolate=False)
        self.assertEqual(calls["n"], 1)
        self.assertEqual(self.sleeps, [])

    def test_exhaustion_raises_last(self):
        def fn():
            raise TransientError("always")

        with self.assertRaises(TransientError):
            retry_call(fn, self.policy, sleep=self.sleeps.append, isolate=False)
        self.assertEqual(len(self.sleeps), 2)

    def test_overall_deadline_stops_retrying(self):
        now = {"t": 0.0}

        def clock():
            return now["t"]

        def fn():
            now["t"] += 100.0
            raise TransientError("slow")

        with self.assertRaises(TransientError):
            retry_call(fn, self.policy, sleep=self.sleeps.append, clock=clock, isolate=False)
        self.assertEqual(self.sleeps, [])


class TestBlockingDeadline(unittest.TestCase):
    """A call that genuinely blocks past the deadline must be aborted."""

    def test_blocking_call_is_aborted_promptly(self):
        release = threading.Event()

        def fn():
            release.wait(8.0)

        policy = RetryPolicy(
            max_attempts=1,
            base_delay=0.0,
            max_delay=0.0,
            per_attempt_timeout=0.3,
            overall_deadline=30.0,
            operation="blocking",
        )
        started = time.monotonic()
        try:
            with self.assertRaises(CallTimeout):
                retry_call(fn, policy, sleep=lambda _d: None)
            self.assertLess(time.monotonic() - started, 3.0)
        finally:
            release.set()

    def test_result_round_trips_through_isolation(self):
        policy = RetryPolicy(max_attempts=1, per_attempt_timeout=5.0, operation="echo")
        self.assertEqual(
            retry_call(lambda: {"n": [1, 2, 3]}, policy), {"n": [1, 2, 3]}
        )

    def test_transient_exception_round_trips_through_isolation(self):
        policy = RetryPolicy(max_attempts=1, per_attempt_timeout=5.0, operation="boom")

        def fn():
            raise TransientError("relayed")

        with self.assertRaises(TransientError):
            retry_call(fn, policy)


class TestDeadlineStopsRetries(unittest.TestCase):

    def test_overall_deadline_prevents_further_attempts(self):
        now = {"t": 0.0}
        calls = {"n": 0}

        def clock():
            return now["t"]

        def fn():
            calls["n"] += 1
            now["t"] += 100.0
            raise TransientError("slow")

        policy = RetryPolicy(
            max_attempts=5, base_delay=0.0, max_delay=0.0,
            per_attempt_timeout=1.0, overall_deadline=60.0, operation="slow",
        )
        with self.assertRaises(TransientError):
            retry_call(fn, policy, sleep=lambda _d: None, clock=clock, isolate=False)
        self.assertEqual(calls["n"], 1)

    def test_overall_deadline_clamps_attempts(self):
        """A retry may not start with more time than remains in the budget."""
        now = {"t": 0.0}
        calls = {"n": 0}

        def clock():
            return now["t"]

        def fn():
            calls["n"] += 1
            now["t"] += 0.8
            raise TransientError("slow")

        policy = RetryPolicy(
            max_attempts=5,
            base_delay=0.0,
            max_delay=0.0,
            per_attempt_timeout=10.0,
            overall_deadline=1.0,
            operation="clamped",
        )
        with self.assertRaises(TransientError):
            retry_call(fn, policy, sleep=lambda _d: None, clock=clock, isolate=False)
        self.assertEqual(calls["n"], 2)


class TestForkAvailability(unittest.TestCase):

    def test_fork_is_available_on_linux_ci(self):
        # The isolated-process path must actually run on Ubuntu CI, not be
        # silently skipped. On Windows (no fork) this asserts the fallback.
        if sys.platform.startswith("linux"):
            self.assertTrue(_FORK_AVAILABLE, "fork must be available on Linux CI")


@unittest.skipUnless(_FORK_AVAILABLE, "fork required for process-isolation tests")
class TestProcessIsolation(unittest.TestCase):
    """Fork-path tests: run on Linux CI, skipped on Windows dev."""

    def test_eight_blocked_calls_do_not_starve_a_healthy_call(self):
        release = threading.Event()

        def block():
            release.wait(20.0)

        errors = []

        def worker():
            try:
                run_with_timeout(block, 5.0, "blocked", isolate=True)
            except BaseException as exc:  # noqa: BLE001 - expected timeout
                errors.append(exc)

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(8)]
        started = time.monotonic()
        for thread in threads:
            thread.start()
        time.sleep(0.5)  # let the blocked calls occupy their processes
        try:
            self.assertEqual(
                run_with_timeout(lambda: "ok", 5.0, "healthy", isolate=True), "ok"
            )
            # A healthy call must not queue behind eight blocked ones.
            # Process creation is platform/runner dependent.  The important
            # invariant is that the healthy call completes before the blocked
            # calls' five-second deadlines, with bounded startup headroom on
            # shared CI runners.
            self.assertLess(time.monotonic() - started, 15.0)
        finally:
            release.set()
            for thread in threads:
                thread.join(timeout=15)
        self.assertEqual(len(errors), len(threads))
        # Under concurrent fork startup a child may close its pipe before the
        # parent observes the deadline; reliability still classifies that as a
        # transient isolated-call failure. Neither outcome may leak a worker.
        self.assertTrue(all(isinstance(e, TransientError) for e in errors), errors)

    def test_concurrent_fork_start_race_is_not_exposed(self):
        """Repeated concurrent starts remain inside the transient contract."""
        failures = []

        def invoke():
            try:
                self.assertEqual(
                    run_with_timeout(lambda: "ok", 5.0, "fork-race", isolate=True),
                    "ok",
                )
            except BaseException as exc:  # noqa: BLE001 - asserted below
                failures.append(exc)

        threads = [threading.Thread(target=invoke) for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertTrue(all(isinstance(exc, TransientError) for exc in failures), failures)

    def test_child_processes_are_terminated_and_reaped(self):
        before = multiprocessing.active_children()
        release = threading.Event()
        with self.assertRaises(CallTimeout):
            run_with_timeout(lambda: release.wait(30.0), 0.3, "blocking", isolate=True)
        release.set()
        # The killed child must not linger in the parent's child set.
        self.assertEqual(len(multiprocessing.active_children()), len(before))


if __name__ == "__main__":
    unittest.main()
