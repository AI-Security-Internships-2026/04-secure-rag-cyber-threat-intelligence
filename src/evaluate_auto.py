import chromadb
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from privacy_filter import is_prompt_injection
from privacy_filter_v2 import redact_with_presidio

# Connect to ChromaDB
client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

# 10 test queries with predefined expected technique names
TEST_QUERIES_WITH_EXPECTED = [
    {
        "query": "ransomware encrypting files for extortion",
        "expected": ["Data Encrypted for Impact", "Inhibit System Recovery", "Selective Exclusion"]
    },
    {
        "query": "phishing email to steal credentials",
        "expected": ["Phishing", "Spearphishing Attachment", "Spearphishing Link"]
    },
    {
        "query": "lateral movement across network using stolen credentials",
        "expected": ["Lateral Movement", "Pass the Hash", "Remote Services"]
    },
    {
        "query": "data exfiltration to external server",
        "expected": ["Exfiltration Over C2 Channel", "Exfiltration Over Web Service", "Transfer Data to Cloud Account"]
    },
    {
        "query": "privilege escalation to gain admin access",
        "expected": ["Abuse Elevation Control Mechanism", "Access Token Manipulation", "Exploitation for Privilege Escalation"]
    },
    {
        "query": "command and control communication with malware",
        "expected": ["Application Layer Protocol", "Encrypted Channel", "Non-Standard Port"]
    },
    {
        "query": "defense evasion by disabling security tools",
        "expected": ["Impair Defenses", "Disable or Modify Tools", "Indicator Removal"]
    },
    {
        "query": "password dumping from memory",
        "expected": ["OS Credential Dumping", "LSASS Memory", "Credentials from Password Stores"]
    },
    {
        "query": "persistence mechanism after system reboot",
        "expected": ["Boot or Logon Autostart Execution", "Scheduled Task/Job", "Create or Modify System Process"]
    },
    {
        "query": "reconnaissance scanning open ports and services",
        "expected": ["Network Service Discovery", "Active Scanning", "Network Service Scanning"]
    },
]

def evaluate_auto():
    print("=" * 60)
    print("AUTOMATIC RETRIEVAL EVALUATION — MITRE ATT&CK RAG PIPELINE")
    print("=" * 60)

    total_queries = 0
    total_precision = 0

    results_log = []

    for i, test in enumerate(TEST_QUERIES_WITH_EXPECTED):
        query = test["query"]
        expected = test["expected"]

        print(f"\nQuery {i+1}: {query}")
        print(f"Expected techniques: {expected}")
        print("-" * 50)

        if is_prompt_injection(query):
            print("BLOCKED: Prompt injection detected.")
            continue

        results = collection.query(query_texts=[query], n_results=3)

        retrieved_names = [meta["name"] for meta in results["metadatas"][0]]

        # Check how many retrieved results match expected
        relevant = 0
        for name in retrieved_names:
            # Partial match — check if expected technique name appears in retrieved name
            matched = any(
                exp.lower() in name.lower() or name.lower() in exp.lower()
                for exp in expected
            )
            status = "✅" if matched else "❌"
            print(f"  {status} {name}")
            if matched:
                relevant += 1

        precision = relevant / len(retrieved_names)
        print(f"  Precision: {precision:.2f} ({precision*100:.0f}%)")

        total_precision += precision
        total_queries += 1

        results_log.append({
            "query": query,
            "retrieved": retrieved_names,
            "expected": expected,
            "precision": precision
        })

    print("\n" + "=" * 60)
    print("OVERALL EVALUATION RESULTS")
    print("=" * 60)
    avg_precision = total_precision / total_queries if total_queries > 0 else 0
    print(f"Queries evaluated: {total_queries}")
    print(f"Average Precision@3: {avg_precision:.2f} ({avg_precision*100:.1f}%)")
    print("=" * 60)

    # Save results to file
    import json
    os.makedirs("experiments/results", exist_ok=True)
    with open("experiments/results/evaluation_auto.json", "w") as f:
        json.dump({
            "average_precision": avg_precision,
            "results": results_log
        }, f, indent=2)
    print("\nResults saved to experiments/results/evaluation_auto.json")


if __name__ == "__main__":
    evaluate_auto()