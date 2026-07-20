import time
import statistics
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import chromadb
from privacy_filter import is_prompt_injection
from privacy_filter_v2 import redact_with_presidio

client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

# Diverse queries so nothing is cached or repeated
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

def run_cpu_only_pipeline(query: str) -> float:
    """
    Runs everything EXCEPT the LLM call.
    Returns total time in seconds for this single request.
    """
    t_start = time.perf_counter()

    # Stage 1 — injection check
    if is_prompt_injection(query):
        return time.perf_counter() - t_start

    # Stage 2 — retrieval
    results = collection.query(query_texts=[query], n_results=3)

    # Stage 3 — privacy filter (Presidio)
    for doc in results["documents"][0]:
        redact_with_presidio(doc)

    return time.perf_counter() - t_start


def run_benchmark(duration_seconds: int = 30):
    print("=" * 60)
    print("CPU-ONLY PIPELINE BENCHMARK (no LLM call)")
    print("=" * 60)
    print(f"Running for {duration_seconds} seconds, cycling through {len(TEST_QUERIES)} unique queries...")
    print()

    latencies = []
    completed = 0
    t_benchmark_start = time.perf_counter()
    query_index = 0

    while time.perf_counter() - t_benchmark_start < duration_seconds:
        query = TEST_QUERIES[query_index % len(TEST_QUERIES)]
        latency = run_cpu_only_pipeline(query)
        latencies.append(latency)
        completed += 1
        query_index += 1

    total_time = time.perf_counter() - t_benchmark_start
    throughput = completed / total_time

    latencies_ms = [l * 1000 for l in latencies]
    latencies_ms.sort()

    result = {
        "test_type": "cpu_only_no_llm",
        "description": "Measures raw CPU throughput for injection check + ChromaDB retrieval + Presidio privacy filter, with LLM generation completely excluded.",
        "duration_seconds": round(total_time, 2),
        "total_requests_completed": completed,
        "requests_per_second": round(throughput, 2),
        "avg_latency_ms": round(statistics.mean(latencies_ms), 2),
        "median_latency_ms": round(statistics.median(latencies_ms), 2),
        "min_latency_ms": round(min(latencies_ms), 2),
        "max_latency_ms": round(max(latencies_ms), 2),
        "p95_latency_ms": round(latencies_ms[int(len(latencies_ms) * 0.95)], 2),
        "p99_latency_ms": round(latencies_ms[int(len(latencies_ms) * 0.99)], 2),
    }

    print(f"Total requests completed: {completed}")
    print(f"Requests per second (CPU only, no LLM): {throughput:.2f}")
    print(f"Average latency: {result['avg_latency_ms']}ms")
    print(f"Median latency: {result['median_latency_ms']}ms")
    print(f"P95 latency: {result['p95_latency_ms']}ms")
    print(f"P99 latency: {result['p99_latency_ms']}ms")
    print("=" * 60)

    return result


if __name__ == "__main__":
    import psutil
    import platform

    result = run_benchmark(duration_seconds=30)

    hardware = {
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "cpu_cores_logical": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "os": platform.system(),
        "gpu": "None — CPU only"
    }

    final = {
        "test_date": time.strftime("%Y-%m-%d"),
        "hardware": hardware,
        **result
    }

    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/cpu_only_benchmark.json", "w") as f:
        json.dump(final, f, indent=2)

    print(f"\nResults saved to experiments/results/cpu_only_benchmark.json")