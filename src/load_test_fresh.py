from locust import HttpUser, task, between
import random
import itertools

# Base query templates — combined with unique IDs to guarantee every request is fresh
BASE_QUERIES = [
    "how does ransomware technique variant {} encrypt files",
    "what is phishing method {} used for credential theft",
    "how do attackers use lateral movement approach {}",
    "what exfiltration technique {} sends data externally",
    "how does privilege escalation method {} gain admin access",
]

VALID_API_KEYS = [f"analyst-key-{str(i).zfill(3)}" for i in range(1, 11)]

# Global counter ensures every single request across all simulated users is unique
counter = itertools.count()

class FreshQueryUser(HttpUser):
    """
    No cache advantage — every query has a unique ID appended,
    forcing the full pipeline (retrieval + privacy filter + LLM) every time.
    This measures genuine CPU-bound generation throughput.
    """
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.api_key = random.choice(VALID_API_KEYS)

    @task
    def fresh_query(self):
        n = next(counter)
        template = random.choice(BASE_QUERIES)
        query = template.format(n)
        self.client.post(
            "/query",
            json={"query": query, "privacy_method": "presidio"},
            headers={"x-api-key": self.api_key},
            name="fresh_query_no_cache"
        )