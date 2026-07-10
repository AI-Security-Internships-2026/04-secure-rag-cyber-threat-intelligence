from locust import HttpUser, task, between # type: ignore
import random
import time

# Two sets of queries for two different tests
CACHED_QUERIES = [
    "how does ransomware encrypt files",  # same query repeated for cache test
]

FRESH_QUERIES = [
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

VALID_API_KEYS = [f"analyst-key-{str(i).zfill(3)}" for i in range(1, 11)]

class CachePerformanceUser(HttpUser):
    """
    Test 1 — Cache throughput
    Measures how many cached requests system handles per second
    """
    wait_time = between(0.1, 0.3)

    def on_start(self):
        self.api_key = random.choice(VALID_API_KEYS)

    @task(4)
    def cached_query(self):
        self.client.post(
            "/query",
            json={
                "query": CACHED_QUERIES[0],
                "privacy_method": "presidio"
            },
            headers={"x-api-key": self.api_key},
            name="cached_query"
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="health_check")