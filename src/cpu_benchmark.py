"""
cpu_benchmark.py — CPU-only speed comparison of privacy-filtering methods.

Compares three redaction methods head-to-head: Presidio (NER-based),
regex v1 (baseline), and regex v3 (hardened). Reports throughput
(requests/second) and latency (avg, median, p95, p99) for each.

What it does:
1. Pre-fetches documents from ChromaDB once, up front. ChromaDB is not
   queried again after this — everything below runs on this fixed,
   in-memory set of documents.
2. Warms up each method (100 calls) before timing starts, so one-time
   costs like module imports or model loading don't skew the first
   real measurements.
3. Runs 10 rounds. Each round benchmarks all three methods, 5,000 calls
   each, timing only the redaction function call itself per request.
4. Shuffles the order the three methods run in every round, so any
   background drift (e.g. CPU heating up over a long run) gets spread
   evenly across all three instead of unfairly penalizing whichever
   method happens to run first or last.
5. Disables Python's garbage collector during each timed block, so a
   GC pause can't randomly land inside one method's window and make
   it look artificially slower.
6. Averages results across all 10 rounds and reports standard
   deviation alongside each number, showing how consistent the result
   actually is, not just a single value.
7. Computes three speed ratios: regex v1 vs Presidio, regex v3 vs
   Presidio, and regex v3 vs regex v1.
8. Records hardware info (CPU cores, RAM, OS, Python version) alongside
   the results for reproducibility.
9. Saves everything — per-round data, averaged summary, and speed
   ratios — to experiments/results/cpu_only_benchmark.json.
"""
import gc
import json
import os
import platform
import random
import statistics
import sys
import time

import chromadb
import psutil

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from privacy_filter import redact_sensitive_info as redact_sensitive_info_v1
from privacy_filter_v2 import redact_with_presidio
from privacy_filter_v3 import redact_sensitive_info as redact_sensitive_info_v3

# Configuration
ROUNDS = 10
REQUESTS_PER_ROUND = 5000
WARMUP_REQUESTS = 100

METHODS = ["presidio", "regex", "regex_v3"]

TEST_QUERIES = [
    "how does ransomware encrypt files",
    "what is spearphishing and how does it work",
    "how do attackers perform lateral movement",
    "what techniques are used for data exfiltration",
    "how do adversaries escalate privileges",
    "what is command and control communication",
    "how do attackers disable security tools",
    "what is credential dumping",
    "how do attackers maintain persistence",
    "what is network reconnaissance",
    "how do adversaries use living off the land techniques",
    "what is process injection",
    "how do attackers move laterally using remote services",
    "what techniques hide malware from detection",
    "how do attackers abuse valid accounts",
    "what is a watering hole attack",
    "how do adversaries use scheduled tasks for persistence",
    "what is kerberoasting",
    "how do attackers use DNS for command and control",
    "what is a supply chain attack",
]

REDACT_FUNCTIONS = {
    "presidio": redact_with_presidio,
    "regex": redact_sensitive_info_v1,
    "regex_v3": redact_sensitive_info_v3,
}

client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")


def prefetch_documents() -> list:
    """
    Retrieves documents for every test query ONCE, outside any timed loop.
    This fixed corpus is what gets redacted repeatedly during benchmarking —
    ChromaDB is never touched again after this function returns.
    """
    print("Pre-fetching documents (this is the only time ChromaDB gets queried)...")
    docs = []
    for query in TEST_QUERIES:
        results = collection.query(query_texts=[query], n_results=3)
        docs.extend(results["documents"][0])
    print(f"Pre-fetched {len(docs)} documents. ChromaDB will not be queried again.\n")
    return docs


def warmup(docs: list):
    print("=" * 60)
    print("Warm-up")
    print("=" * 60)
    for method in METHODS:
        redact_fn = REDACT_FUNCTIONS[method]
        for i in range(WARMUP_REQUESTS):
            redact_fn(docs[i % len(docs)])
    print("Warm-up complete.\n")


def benchmark_method(method: str, docs: list) -> dict:
    redact_fn = REDACT_FUNCTIONS[method]

    gc.collect()
    gc.disable()

    latencies = []
    start = time.perf_counter()

    for i in range(REQUESTS_PER_ROUND):
        doc = docs[i % len(docs)]
        t0 = time.perf_counter()
        redact_fn(doc)  # ONLY the redaction call is timed — no retrieval here
        latencies.append(time.perf_counter() - t0)

    total_time = time.perf_counter() - start
    gc.enable()

    latencies_ms = sorted(l * 1000 for l in latencies)
    throughput = REQUESTS_PER_ROUND / total_time

    return {
        "requests_per_second": throughput,
        "avg_latency_ms": statistics.mean(latencies_ms),
        "median_latency_ms": statistics.median(latencies_ms),
        "min_latency_ms": min(latencies_ms),
        "max_latency_ms": max(latencies_ms),
        "p95_latency_ms": latencies_ms[int(0.95 * len(latencies_ms))],
        "p99_latency_ms": latencies_ms[int(0.99 * len(latencies_ms))],
    }


def average_rounds(results: list) -> dict:
    summary = {}
    metrics = ["requests_per_second", "avg_latency_ms", "median_latency_ms",
               "min_latency_ms", "max_latency_ms", "p95_latency_ms", "p99_latency_ms"]
    for metric in metrics:
        values = [r[metric] for r in results]
        summary[metric] = round(statistics.mean(values), 4)
        summary[f"{metric}_std"] = round(statistics.stdev(values), 4) if len(values) > 1 else 0
    return summary


if __name__ == "__main__":
    docs = prefetch_documents()
    warmup(docs)

    all_results = {method: [] for method in METHODS}

    print("=" * 70)
    print("STARTING BENCHMARK (redaction-only, retrieval already pre-fetched)")
    print("=" * 70)

    for round_number in range(1, ROUNDS + 1):
        print(f"\nRound {round_number}/{ROUNDS}")
        order = METHODS.copy()
        random.shuffle(order)  # guards against systematic bias (e.g. thermal
                                # throttling always penalizing whichever method
                                # happens to run last)
        print("Execution order:", " -> ".join(order))

        for method in order:
            result = benchmark_method(method, docs)
            all_results[method].append(result)
            print(f"  {method:12s} RPS: {result['requests_per_second']:.2f}  "
                  f"Median: {result['median_latency_ms']:.4f}ms  "
                  f"P99: {result['p99_latency_ms']:.4f}ms")

    print("\n" + "=" * 70)
    print("SUMMARY (averaged across all rounds, ± standard deviation)")
    print("=" * 70)

    summaries = {method: average_rounds(all_results[method]) for method in METHODS}

    for method in METHODS:
        s = summaries[method]
        print(f"{method:12s}: {s['requests_per_second']:.2f} ± {s['requests_per_second_std']:.2f} req/sec  "
              f"| median {s['median_latency_ms']:.4f} ± {s['median_latency_ms_std']:.4f} ms")

    speedup_v1_vs_presidio = summaries["regex"]["requests_per_second"] / summaries["presidio"]["requests_per_second"]
    speedup_v3_vs_presidio = summaries["regex_v3"]["requests_per_second"] / summaries["presidio"]["requests_per_second"]
    v3_vs_v1_ratio = summaries["regex_v3"]["requests_per_second"] / summaries["regex"]["requests_per_second"]

    print()
    print(f"Regex v1 speedup vs Presidio: {speedup_v1_vs_presidio:.2f}x")
    print(f"Regex v3 speedup vs Presidio: {speedup_v3_vs_presidio:.2f}x")
    print(f"Regex v3 vs Regex v1:         {v3_vs_v1_ratio:.3f}x "
          f"({'v3 faster' if v3_vs_v1_ratio > 1 else 'v3 slower' if v3_vs_v1_ratio < 1 else 'no difference'})")
    print("=" * 70)

    hardware = {
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "cpu_cores_logical": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "os": platform.system(),
        "os_version": platform.version(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "gpu": "None (CPU Only)",
    }

    final_results = {
        "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "methodology_note": (
            "Retrieval (ChromaDB query) is performed ONCE up front and excluded "
            "from all timing. Only the redaction function call itself is timed, "
            "per request, per round. This isolates the actual comparison from "
            "ChromaDB's own retrieval-time jitter, which was previously large "
            "enough to mask the true v1-vs-v3 difference and cause flip-flopping "
            "results between runs."
        ),
        "benchmark_configuration": {
            "rounds": ROUNDS,
            "requests_per_round": REQUESTS_PER_ROUND,
            "warmup_requests": WARMUP_REQUESTS,
            "total_requests_per_method": ROUNDS * REQUESTS_PER_ROUND,
            "documents_prefetched": len(docs),
        },
        "hardware": hardware,
        "per_round_results": all_results,
        "summary": summaries,
        "speedups": {
            "regex_v1_vs_presidio": round(speedup_v1_vs_presidio, 3),
            "regex_v3_vs_presidio": round(speedup_v3_vs_presidio, 3),
            "regex_v3_vs_regex_v1": round(v3_vs_v1_ratio, 3),
        },
    }

    os.makedirs("experiments/results", exist_ok=True)
    output_file = "experiments/results/cpu_only_benchmark.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=2)

    print(f"\nResults saved to: {output_file}")