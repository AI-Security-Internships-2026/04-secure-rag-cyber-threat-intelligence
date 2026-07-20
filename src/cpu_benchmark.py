import time
import statistics
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import chromadb
from privacy_filter import is_prompt_injection, redact_sensitive_info
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

def run_pipeline(query: str, privacy_method: str) -> float:
    """
    Runs retrieval + chosen privacy filter method.
    Returns total time in seconds for this single request.
    """
    t_start = time.perf_counter()

    if is_prompt_injection(query):
        return time.perf_counter() - t_start

    results = collection.query(query_texts=[query], n_results=3)

    for doc in results["documents"][0]:
        if privacy_method == "presidio":
            redact_with_presidio(doc)
        else:
            redact_sensitive_info(doc)

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
    regex_result = run_benchmark("regex", duration_seconds=30)

    speedup = regex_result["requests_per_second"] / presidio_result["requests_per_second"]

    print("=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"Presidio (NER):  {presidio_result['requests_per_second']} req/sec, {presidio_result['median_latency_ms']}ms median")
    print(f"Regex:           {regex_result['requests_per_second']} req/sec, {regex_result['median_latency_ms']}ms median")
    print(f"Regex is {speedup:.1f}x faster than Presidio")
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
        "regex": regex_result,
        "regex_speedup_factor": round(speedup, 2)
    }

    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/cpu_only_benchmark.json", "w") as f:
        json.dump(final, f, indent=2)

    print(f"\nResults saved to experiments/results/cpu_only_benchmark.json")