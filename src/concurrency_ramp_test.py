"""
concurrency_ramp_test.py.

At each level (2, 4, 8, 16, 32, 64 threads running in parallel), this:
  1. Spawns that many threads, each repeatedly running the FULL labeled
     accuracy test set (28 cases) through the hardened regex filter
  2. Uses a sleep time that starts at 2.0s and decreases by 0.1s per level
     (2.0, 1.9, 1.8, 1.7, 1.6, 1.5) — more threads AND less waiting between
     requests = steadily increasing pressure on the system
  3. Measures CPU% and RAM% in the background for the WHOLE level's run
     (using resource_monitor.py)
  4. Aggregates every thread's redaction results together and computes
     precision/recall/F1 for that level — this proves accuracy holds up
     under concurrent load, not just that the system stays fast

Deliberately isolated:
  - No LLM call anywhere in this test (measuring the filter, not Groq's
    network latency)
  - No caching — every call runs the real regex work, nothing is skipped

Run: python concurrency_ramp_test.py
(edit DURATION_PER_LEVEL_SECONDS and THREAD_LEVELS below for a quick
 smoke test vs. the full run)
"""

import json
import os
import threading
import time
from itertools import cycle
 
from privacy_filter_v3 import extract_entities
from regex_test_set import TEST_CASES
from resource_monitor import ResourceMonitor
 
# --- Configuration ---
THREAD_LEVELS = [2, 4, 8, 16, 32, 64]
DURATION_PER_LEVEL_SECONDS = 15   # how long each thread level runs for
SLEEP_START = 2.0
SLEEP_STEP = 0.1                  # decreases by this much each level
 
 
def worker(stop_event, sleep_time, shared_counters, lock, case_cycle):
    """
    Each thread runs this. Pulls the NEXT case from a shared, thread-safe
    cycle (itertools.cycle().__next__ is atomic under CPython's GIL) so
    the full 28-case test set gets covered across all threads combined,
    instead of every thread independently restarting at index 0 and never
    reaching cases near the end of the list before time runs out.
    """
    local_tp, local_fp, local_fn, local_requests = 0, 0, 0, 0
 
    while not stop_event.is_set():
        case = next(case_cycle)
        predicted = set(extract_entities(case["text"]))
        expected = set(case["expected"])
        local_tp += len(predicted & expected)
        local_fp += len(predicted - expected)
        local_fn += len(expected - predicted)
        local_requests += 1
 
        time.sleep(sleep_time)
 
    with lock:
        shared_counters["tp"] += local_tp
        shared_counters["fp"] += local_fp
        shared_counters["fn"] += local_fn
        shared_counters["requests"] += local_requests
 
 
def run_level(thread_count: int, sleep_time: float, duration: float) -> dict:
    print(f"\n{'='*60}")
    print(f"LEVEL: {thread_count} threads | sleep={sleep_time:.1f}s | duration={duration}s")
    print(f"{'='*60}")
 
    stop_event = threading.Event()
    lock = threading.Lock()
    shared_counters = {"tp": 0, "fp": 0, "fn": 0, "requests": 0}
    case_cycle = cycle(TEST_CASES)  # shared across all threads — see worker() docstring
 
    monitor = ResourceMonitor(sample_interval=0.5)
    monitor.start()
 
    threads = [
        threading.Thread(target=worker, args=(stop_event, sleep_time, shared_counters, lock, case_cycle))
        for _ in range(thread_count)
    ]
 
    t_start = time.perf_counter()
    for t in threads:
        t.start()
 
    time.sleep(duration)
    stop_event.set()
    for t in threads:
        t.join(timeout=sleep_time + 2)
    elapsed = time.perf_counter() - t_start
 
    resource_stats = monitor.stop()
 
    tp, fp, fn = shared_counters["tp"], shared_counters["fp"], shared_counters["fn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
 
    result = {
        "thread_count": thread_count,
        "sleep_time_seconds": sleep_time,
        "elapsed_seconds": round(elapsed, 2),
        "total_requests": shared_counters["requests"],
        "requests_per_second": round(shared_counters["requests"] / elapsed, 2),
        "accuracy": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        },
        "resources": resource_stats,
    }
 
    print(f"  Requests processed: {result['total_requests']} ({result['requests_per_second']} req/sec)")
    print(f"  Accuracy — Precision: {precision*100:.1f}% Recall: {recall*100:.1f}% F1: {f1*100:.1f}%")
    print(f"  CPU — avg: {resource_stats['avg_cpu_pct']}% max: {resource_stats['max_cpu_pct']}%")
    print(f"  RAM — avg: {resource_stats['avg_ram_pct']}% max: {resource_stats['max_ram_pct']}%")
 
    return result
 
 
def main():
    print("CONCURRENCY RAMP TEST — regex privacy filter under parallel load")
    print(f"Thread levels: {THREAD_LEVELS}")
    print(f"Sleep ramps from {SLEEP_START}s, decreasing {SLEEP_STEP}s per level")
 
    results = []
    for i, thread_count in enumerate(THREAD_LEVELS):
        sleep_time = round(SLEEP_START - (i * SLEEP_STEP), 2)
        result = run_level(thread_count, sleep_time, DURATION_PER_LEVEL_SECONDS)
        results.append(result)
        time.sleep(3)  # brief cooldown between levels so one level doesn't bleed into the next
 
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experiments", "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "concurrency_ramp_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d"),
            "config": {
                "thread_levels": THREAD_LEVELS,
                "duration_per_level_seconds": DURATION_PER_LEVEL_SECONDS,
                "sleep_start": SLEEP_START,
                "sleep_step": SLEEP_STEP,
            },
            "results": results,
        }, f, indent=2)
 
    print(f"\nSaved: {output_path}")
 
 
if __name__ == "__main__":
    main()
 