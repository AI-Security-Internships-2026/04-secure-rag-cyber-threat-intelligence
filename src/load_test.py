from locust import HttpUser, task, between
import random

API_KEYS = ["analyst-key-001", "admin-key-001", "guest-key-001"]

class CTIPipelineUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.api_key = random.choice(API_KEYS)

    @task
    def query_ransomware(self):
        self.client.post(
            "/query",
            json={"query": "how does ransomware encrypt files", "privacy_method": "presidio"},
            headers={"x-api-key": self.api_key}
        )

    @task
    def query_phishing(self):
        self.client.post(
            "/query",
            json={"query": "what is spearphishing", "privacy_method": "presidio"},
            headers={"x-api-key": self.api_key}
        )

    @task
    def health_check(self):
        self.client.get("/health")