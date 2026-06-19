import chromadb

client = chromadb.Client()
collection = client.create_collection("test_cti")

collection.add(
    documents=["Ransomware campaign targeting healthcare sector using phishing emails."],
    ids=["doc1"]
)

results = collection.query(query_texts=["ransomware attack"], n_results=1)
print("ChromaDB working!")
print(results)