import os
import subprocess
import sys

from scripts.benchmark_warm_queries import percentile


def test_percentile_interpolates():
    assert percentile([10, 20, 30, 40], 50) == 25
    assert percentile([], 95) == 0.0


def test_benchmark_script_requires_token():
    env = os.environ.copy()
    env.pop("FIREBASE_ID_TOKEN", None)
    proc = subprocess.run(
        [sys.executable, "scripts/benchmark_warm_queries.py", "--url", "http://127.0.0.1:1",
         "--query", "about", "--runs", "1", "--out", "benchmark-test.json"],
        env=env, capture_output=True, text=True,
    )
    assert proc.returncode != 0
