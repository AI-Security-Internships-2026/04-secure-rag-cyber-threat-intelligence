import time
import statistics
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import chromadb
from privacy_filter import is_prompt_injection, redact_sensitive_info as redact_sensitive_info_v1
from privacy_filter_v3 import redact_sensitive_info as redact_sensitive_info_v3
from privacy_filter_v2 import redact_with_presidio

client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

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

# privacy_method -> which redaction function to call. Fixes the earlier bug
# where "regex_v3" silently fell through to the v1 baseline in the else branch.
REDACT_FUNCTIONS = {
    "presidio": redact_with_presidio,
    "regex": redact_sensitive_info_v1,      # v1 baseline — kept for comparison
    "regex_v3": redact_sensitive_info_v3,   # hardened version, now the real path
}


def run_pipeline(query: str, privacy_method: str) -> float:
    """
    Runs retrieval + chosen privacy filter method.
    Returns total time in seconds for this single request.
    """
    t_start = time.perf_counter()

    if is_prompt_injection(query):
        return time.perf_counter() - t_start

    results = collection.query(query_texts=[query], n_results=3)

    redact_fn = REDACT_FUNCTIONS[privacy_method]
    for doc in results["documents"][0]:
        redact_fn(doc)

    return time.perf_counter() - t_start


def run_benchmark(privacy_method: str, duration_seconds: int = 30):
    print("=" * 60)
    print(f"CPU-ONLY BENCHMARK — privacy method: {privacy_method}")
    print("=" * 60)

    latencies = []
    completed = 0
    t_benchmark_start = time.perf_counter()
    query_index = 0

    while time.perf_counter() - t_benchmark_start < duration_seconds:
        query = TEST_QUERIES[query_index % len(TEST_QUERIES)]
        latency = run_pipeline(query, privacy_method)
        latencies.append(latency)
        completed += 1
        query_index += 1

    total_time = time.perf_counter() - t_benchmark_start
    throughput = completed / total_time

    latencies_ms = sorted([l * 1000 for l in latencies])

    result = {
        "privacy_method": privacy_method,
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

    print(f"Requests/sec: {throughput:.2f}")
    print(f"Median latency: {result['median_latency_ms']}ms")
    print(f"P95 latency: {result['p95_latency_ms']}ms")
    print(f"P99 latency: {result['p99_latency_ms']}ms")
    print()

    return result


if __name__ == "__main__":
    import psutil
    import platform

    presidio_result = run_benchmark("presidio", duration_seconds=30)
    regex_v1_result = run_benchmark("regex", duration_seconds=30)
    regex_v3_result = run_benchmark("regex_v3", duration_seconds=30)

    speedup_v1_vs_presidio = regex_v1_result["requests_per_second"] / presidio_result["requests_per_second"]
    speedup_v3_vs_presidio = regex_v3_result["requests_per_second"] / presidio_result["requests_per_second"]
    v3_vs_v1_ratio = regex_v3_result["requests_per_second"] / regex_v1_result["requests_per_second"]

    print("=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"Presidio (NER):   {presidio_result['requests_per_second']} req/sec, {presidio_result['median_latency_ms']}ms median")
    print(f"Regex v1:         {regex_v1_result['requests_per_second']} req/sec, {regex_v1_result['median_latency_ms']}ms median")
    print(f"Regex v3:         {regex_v3_result['requests_per_second']} req/sec, {regex_v3_result['median_latency_ms']}ms median")
    print(f"Regex v1 is {speedup_v1_vs_presidio:.1f}x faster than Presidio")
    print(f"Regex v3 is {speedup_v3_vs_presidio:.1f}x faster than Presidio")
    print(f"Regex v3 vs v1 speed ratio: {v3_vs_v1_ratio:.2f}x (checking hardening didn't cost noticeable speed)")
    print("=" * 60)

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
        "presidio": presidio_result,
        "regex_v1_baseline": regex_v1_result,
        "regex_v3_hardened": regex_v3_result,
        "regex_v1_speedup_vs_presidio": round(speedup_v1_vs_presidio, 2),
        "regex_v3_speedup_vs_presidio": round(speedup_v3_vs_presidio, 2),
        "regex_v3_vs_v1_speed_ratio": round(v3_vs_v1_ratio, 2),
    }

    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/cpu_only_benchmark.json", "w") as f:
        json.dump(final, f, indent=2)

    print(f"\nResults saved to experiments/results/cpu_only_benchmark.json")