import chromadb # type: ignore
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from privacy_filter import redact_sensitive_info, is_prompt_injection
from privacy_filter_v2 import redact_with_presidio

# Connect to ChromaDB
client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

# Change this for P@N_RESULTS evaluation
N_RESULTS = 10

# 10 test queries covering different attack categories
TEST_QUERIES = [
    "ransomware encrypting files for extortion",
    "phishing email to steal credentials",
    "lateral movement across network using stolen credentials",
    "data exfiltration to external server",
    "privilege escalation to gain admin access",
    "command and control communication with malware",
    "defense evasion by disabling security tools",
    "password dumping from memory",
    "persistence mechanism after system reboot",
    "reconnaissance scanning open ports and services",
]

def evaluate_query(query: str) -> dict:
    """
    Runs a single query and returns results for manual relevance judgment.
    """
    if is_prompt_injection(query):
        return {"query": query, "blocked": True, "results": []}

    results = collection.query(query_texts=[query], n_results=N_RESULTS)

    retrieved = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        redacted_doc, _ = redact_with_presidio(doc)
        retrieved.append({
            "name": meta["name"],
            "description": redacted_doc[:200]
        })

    return {
        "query": query,
        "blocked": False,
        "results": retrieved
    }


def run_evaluation():
    print("=" * 60)
    print(f"MANUAL RETRIEVAL EVALUATION — P@{N_RESULTS}")
    print("=" * 60)

    total_results = 0
    total_relevant = 0
    results_log = []

    for i, query in enumerate(TEST_QUERIES):
        print(f"\nQuery {i+1}: {query}")
        print("-" * 50)

        output = evaluate_query(query)

        if output["blocked"]:
            print("BLOCKED: Prompt injection detected.")
            continue

        query_relevant = 0
        query_results = []

        for j, result in enumerate(output["results"]):
            print(f"  Result {j+1}: {result['name']}")
            print(f"  Preview: {result['description']}...")
            print()

            # Manual relevance judgment
            while True:
                judgment = input(f"  Is Result {j+1} relevant? (y/n/p for partial): ").strip().lower()
                if judgment in ["y", "n", "p"]:
                    break
                print("  Please enter y, n, or p")

            total_results += 1
            score = 0
            if judgment == "y":
                total_relevant += 1
                query_relevant += 1
                score = 1
            elif judgment == "p":
                total_relevant += 0.5
                query_relevant += 0.5
                score = 0.5

            query_results.append({
                "name": result["name"],
                "judgment": judgment,
                "score": score
            })

        query_precision = query_relevant / N_RESULTS
        results_log.append({
            "query": query,
            "results": query_results,
            "precision": query_precision
        })

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    precision = total_relevant / total_results if total_results > 0 else 0
    print(f"Metric: Precision@{N_RESULTS}")
    print(f"Total results evaluated: {total_results}")
    print(f"Relevant results: {total_relevant}")
    print(f"Average Precision@{N_RESULTS}: {precision:.2f} ({precision*100:.1f}%)")
    print("=" * 60)

    # Save results with dynamic filename
    os.makedirs("experiments/results", exist_ok=True)
    output_path = f"experiments/results/evaluation_manual_p{N_RESULTS}.json"
    with open(output_path, "w") as f:
        json.dump({
            "metric": f"Precision@{N_RESULTS}",
            "average_precision": precision,
            "n_results": N_RESULTS,
            "total_results": total_results,
            "total_relevant": total_relevant,
            "results": results_log
        }, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    run_evaluation()