import json
import chromadb

# Load real MITRE ATT&CK STIX bundle
with open("data/mitre_attack.json", "r") as f:
    bundle = json.load(f)

# Extract only attack-pattern objects (techniques)
techniques = [
    obj for obj in bundle["objects"]
    if obj.get("type") == "attack-pattern"
    and obj.get("description")
]

print(f"Loaded {len(techniques)} attack techniques from MITRE ATT&CK")

# Set up ChromaDB
client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

# Load techniques into ChromaDB
documents = []
metadatas = []
ids = []

for i, technique in enumerate(techniques):
    documents.append(technique["description"])
    metadatas.append({
        "name": technique.get("name", "Unknown"),
        "type": technique.get("type", ""),
        "stix_id": technique.get("id", str(i))
    })
    ids.append(str(i))

collection.add(
    documents=documents,
    metadatas=metadatas,
    ids=ids
)

print(f"Successfully ingested {len(documents)} techniques into ChromaDB")