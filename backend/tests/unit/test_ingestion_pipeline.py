from __future__ import annotations

from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from job_discovery_backend.ingestion.pipeline import run_in_parallel  # noqa: E402


def test_run_in_parallel_honors_worker_bound_and_preserves_input_order() -> None:
    active_workers = 0
    peak_workers = 0
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def worker(item: int) -> int:
        nonlocal active_workers, peak_workers
        with lock:
            active_workers += 1
            peak_workers = max(peak_workers, active_workers)
        if item in {1, 2}:
            barrier.wait(timeout=1)
        time.sleep(0.01)
        with lock:
            active_workers -= 1
        return item * 10

    results = run_in_parallel([1, 2, 3], worker, max_workers=2)

    assert results == [10, 20, 30]
    assert peak_workers == 2
