import chromadb # type: ignore
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from privacy_filter import is_prompt_injection

# Connect to ChromaDB
client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

# Change this for P@N_RESULTS evaluation
N_RESULTS = 10

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

def exact_match(retrieved_name: str, expected_list: list) -> bool:
    retrieved_lower = retrieved_name.lower()
    return any(
        exp.lower() in retrieved_lower or retrieved_lower in exp.lower()
        for exp in expected_list
    )

def semantic_match(retrieved_name: str, expected_list: list) -> float:
    results = collection.query(
        query_texts=[retrieved_name],
        n_results=3
    )
    retrieved_names = [meta["name"] for meta in results["metadatas"][0]]
    for name in retrieved_names:
        if any(exp.lower() in name.lower() or name.lower() in exp.lower()
               for exp in expected_list):
            return 1.0
    return 0.0

def evaluate_combo():
    print("=" * 60)
    print(f"COMBINED EVALUATION — EXACT + SEMANTIC MATCHING — P@{N_RESULTS}")
    print("=" * 60)

    exact_total = 0
    semantic_total = 0
    combo_total = 0
    total_queries = 0
    results_log = []

    for i, test in enumerate(TEST_QUERIES_WITH_EXPECTED):
        query = test["query"]
        expected = test["expected"]

        print(f"\nQuery {i+1}: {query}")
        print(f"Expected: {expected}")
        print("-" * 50)

        if is_prompt_injection(query):
            print("BLOCKED: Prompt injection detected.")
            continue

        results = collection.query(query_texts=[query], n_results=N_RESULTS)
        retrieved_names = [meta["name"] for meta in results["metadatas"][0]]

        query_exact = 0
        query_semantic = 0
        query_combo = 0

        for name in retrieved_names:
            is_exact = exact_match(name, expected)
            is_semantic = semantic_match(name, expected) > 0.0
            is_combo = is_exact or is_semantic

            exact_icon = "✅" if is_exact else "❌"
            semantic_icon = "✅" if is_semantic else "❌"
            combo_icon = "✅" if is_combo else "❌"

            print(f"  {name}")
            print(f"    Exact: {exact_icon}  Semantic: {semantic_icon}  Combined: {combo_icon}")

            if is_exact:
                query_exact += 1
            if is_semantic:
                query_semantic += 1
            if is_combo:
                query_combo += 1

        n = len(retrieved_names)
        print(f"  Precision@{N_RESULTS} — Exact: {query_exact/n:.2f} | Semantic: {query_semantic/n:.2f} | Combined: {query_combo/n:.2f}")

        exact_total += query_exact / n
        semantic_total += query_semantic / n
        combo_total += query_combo / n
        total_queries += 1

        results_log.append({
            "query": query,
            "retrieved": retrieved_names,
            "expected": expected,
            "exact_precision": query_exact / n,
            "semantic_precision": query_semantic / n,
            "combo_precision": query_combo / n
        })

    print("\n" + "=" * 60)
    print("OVERALL EVALUATION RESULTS")
    print("=" * 60)
    print(f"Metric: Precision@{N_RESULTS}")
    print(f"Queries evaluated: {total_queries}")
    print(f"Exact Match Precision@{N_RESULTS}:    {exact_total/total_queries:.2f} ({exact_total/total_queries*100:.1f}%)")
    print(f"Semantic Match Precision@{N_RESULTS}: {semantic_total/total_queries:.2f} ({semantic_total/total_queries*100:.1f}%)")
    print(f"Combined Precision@{N_RESULTS}:       {combo_total/total_queries:.2f} ({combo_total/total_queries*100:.1f}%)")
    print(f"Manual Precision@{N_RESULTS}:         0.78 (78.3%) — from evaluate_manual.py")
    print("=" * 60)

    # Save results with dynamic filename
    os.makedirs("experiments/results", exist_ok=True)
    output_path = f"experiments/results/evaluation_combined_p{N_RESULTS}.json"
    with open(output_path, "w") as f:
        json.dump({
            "metric": f"Precision@{N_RESULTS}",
            "n_results": N_RESULTS,
            "exact_precision": exact_total / total_queries,
            "semantic_precision": semantic_total / total_queries,
            "combo_precision": combo_total / total_queries,
            "manual_precision": 0.783,
            "results": results_log
        }, f, indent=2)
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    evaluate_combo()