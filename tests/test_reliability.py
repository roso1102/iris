"""Phase 0.1 tests — bounded retry/timeout policy."""

import threading
import time
import unittest
from unittest.mock import MagicMock

from services.common.reliability import (
    CallTimeout,
    PermanentError,
    RetryPolicy,
    TransientError,
    classify_exception,
    is_transient_status,
    retry_after_from_headers,
    retry_call,
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


if __name__ == "__main__":
    unittest.main()
