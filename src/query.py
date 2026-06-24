import chromadb

# Connect to the saved ChromaDB database
client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

# Query
query = "ransomware encrypting files for extortion"

results = collection.query(
    query_texts=[query],
    n_results=3
)

print(f"\nQuery: {query}\n")
print("Top 3 matching techniques:\n")

for i, (doc, meta) in enumerate(zip(
    results["documents"][0],
    results["metadatas"][0]
)):
    print(f"Result {i+1}: {meta['name']}")
    print(f"Description: {doc[:300]}...")
    print()
    