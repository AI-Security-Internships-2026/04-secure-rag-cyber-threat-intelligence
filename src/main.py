from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import chromadb
import json
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from privacy_filter import redact_sensitive_info, is_prompt_injection
from privacy_filter_v2 import redact_with_presidio
from llm import generate_response

app = FastAPI(title="Secure RAG CTI Pipeline")

# ChromaDB
client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

# Stub auth — just checks if any key is provided
VALID_API_KEYS = ["analyst-key-001", "admin-key-001", "guest-key-001"]

# Stats
stats = {"total_queries": 0, "blocked_queries": 0, "start_time": time.time()}

class QueryRequest(BaseModel):
    query: str
    privacy_method: str = "presidio"

@app.get("/health")
def health():
    return {"status": "ok", "message": "Secure RAG CTI Pipeline is running"}

@app.get("/stats")
def get_stats():
    return {
        "total_queries": stats["total_queries"],
        "blocked_queries": stats["blocked_queries"],
        "uptime_seconds": int(time.time() - stats["start_time"])
    }

@app.post("/query")
def query(request: QueryRequest, x_api_key: str = Header(...)):
    # Stub auth check
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")

    stats["total_queries"] += 1

    # Stage 1 — Prompt injection check
    if is_prompt_injection(request.query):
        stats["blocked_queries"] += 1
        raise HTTPException(status_code=400, detail="Query blocked: prompt injection detected")

    # Stage 2 — Retrieve from ChromaDB
    results = collection.query(query_texts=[request.query], n_results=3)

    # Stage 3 — Privacy filter
    clean_chunks = []
    redacted_items = []

    for doc in results["documents"][0]:
        if request.privacy_method == "presidio":
            redacted_doc, found = redact_with_presidio(doc)
        else:
            redacted_doc, found = redact_sensitive_info(doc)
        clean_chunks.append(redacted_doc)
        redacted_items.extend(found)

    # Stage 4 — LLM Generation
    answer = generate_response(request.query, clean_chunks)

    # Log to file
    os.makedirs("logs", exist_ok=True)
    with open("logs/queries.json", "a") as f:
        json.dump({
            "timestamp": time.time(),
            "api_key": x_api_key,
            "query": request.query,
            "blocked": False,
            "sources": [m["name"] for m in results["metadatas"][0]],
            "redacted_items": redacted_items
        }, f)
        f.write("\n")

    return {
        "query": request.query,
        "answer": answer,
        "sources": [m["name"] for m in results["metadatas"][0]],
        "redacted_items": redacted_items
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)