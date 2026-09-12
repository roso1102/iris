"""Linux CI gate for the process-isolation deadline primitive.

Runs only meaningfully on Linux. Exits non-zero if:
  * ``fork`` is unavailable (so process isolation could not be exercised);
  * a blocked call is not killed at its deadline, or overruns it;
  * a healthy call is starved;
  * any child process survives.

This proves the *primitive*, not real Vertex integration — that requires the
credentialed canary (``scripts/canary_vertex_ops.py``).
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from services.common.reliability import (
        _FORK_AVAILABLE,
        CallTimeout,
        run_with_timeout,
    )

    failures: list[str] = []
    print(f"sys.platform={sys.platform}")
    print(f"_FORK_AVAILABLE={_FORK_AVAILABLE}")
    if not _FORK_AVAILABLE:
        failures.append("fork unavailable: process isolation cannot be verified")

    before = multiprocessing.active_children()

    started = time.monotonic()
    killed = False
    try:
        run_with_timeout(lambda: time.sleep(30), 0.5, "ci.blocked", isolate=True)
    except CallTimeout:
        killed = True
    elapsed = time.monotonic() - started
    print(f"blocked_call_killed={killed} elapsed_ms={elapsed * 1000:.0f}")
    if not killed:
        failures.append("blocked call was not killed at the deadline")
    if elapsed > 5.0:
        failures.append(f"deadline overrun: {elapsed:.2f}s > 5s")

    healthy = run_with_timeout(lambda: "ok", 5.0, "ci.healthy", isolate=True)
    print(f"healthy_call_result={healthy!r}")
    if healthy != "ok":
        failures.append("healthy call did not complete")

    survivors = [c for c in multiprocessing.active_children() if c not in before]
    print(f"surviving_children={len(survivors)}")
    if survivors:
        failures.append(f"{len(survivors)} child process(es) survived")

    if failures:
        print("RESULT: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("RESULT: PASS — process isolation verified on Linux")
    return 0


if __name__ == "__main__":
    sys.exit(main())
