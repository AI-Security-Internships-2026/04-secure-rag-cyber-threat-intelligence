from fastapi import FastAPI, Header, HTTPException # type: ignore
from fastapi.responses import HTMLResponse # type: ignore
from pydantic import BaseModel # type: ignore
from dotenv import load_dotenv # type: ignore
import chromadb # type: ignore
import json
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from privacy_filter import redact_sensitive_info, is_prompt_injection
from privacy_filter_v2 import redact_with_presidio
from llm import generate_response
from cache import get_cached, set_cache, get_cache_stats
from output_scanner import scan_output

app = FastAPI(title="Secure RAG CTI Pipeline")

# ChromaDB
client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

# Stub auth
VALID_API_KEYS = {
    "analyst-key-001": "analyst",
    "admin-key-001": "admin",
    "guest-key-001": "guest"
}

# Rate limiting
request_counts = {}
RATE_LIMIT = 10

# Stats
stats = {
    "total_queries": 0,
    "blocked_queries": 0,
    "cache_hits": 0,
    "output_leaks_caught": 0,
    "start_time": time.time()
}

class QueryRequest(BaseModel):
    query: str
    privacy_method: str = "presidio"

def check_rate_limit(api_key: str) -> bool:
    current_minute = int(time.time() / 60)
    key = f"{api_key}:{current_minute}"
    request_counts[key] = request_counts.get(key, 0) + 1
    return request_counts[key] <= RATE_LIMIT

@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "Secure RAG CTI Pipeline is running"
    }

@app.get("/stats")
def get_stats(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {
        "total_queries": stats["total_queries"],
        "blocked_queries": stats["blocked_queries"],
        "cache_hits": stats["cache_hits"],
        "output_leaks_caught": stats["output_leaks_caught"],
        "uptime_seconds": int(time.time() - stats["start_time"]),
        "cache": get_cache_stats()
    }

@app.post("/query")
def query(request: QueryRequest, x_api_key: str = Header(...)):
    # Auth check
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Rate limit check
    if not check_rate_limit(x_api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    stats["total_queries"] += 1

    # Stage 1 — Prompt injection check
    if is_prompt_injection(request.query):
        stats["blocked_queries"] += 1
        raise HTTPException(status_code=400, detail="Query blocked: prompt injection detected")

    # Stage 2 — Cache check
    cached = get_cached(request.query, request.privacy_method)
    if cached:
        stats["cache_hits"] += 1
        cached["from_cache"] = True
        return cached

    # Stage 3 — Retrieve from ChromaDB
    results = collection.query(query_texts=[request.query], n_results=3)

    # Stage 4 — Privacy filter
    clean_chunks = []
    redacted_items = []

    for doc in results["documents"][0]:
        if request.privacy_method == "presidio":
            redacted_doc, found = redact_with_presidio(doc)
        else:
            redacted_doc, found = redact_sensitive_info(doc)
        clean_chunks.append(redacted_doc)
        redacted_items.extend(found)

    # Stage 5 — LLM Generation
    answer = generate_response(request.query, clean_chunks)

    # Stage 6 — Output scanner
    cleaned_answer, leaked_items, leaked = scan_output(answer)
    if leaked:
        stats["output_leaks_caught"] += 1
        redacted_items.extend(leaked_items)

    result = {
        "query": request.query,
        "answer": cleaned_answer,
        "sources": [m["name"] for m in results["metadatas"][0]],
        "redacted_items": redacted_items,
        "from_cache": False
    }

    # Stage 7 — Cache result
    set_cache(request.query, request.privacy_method, result)

    # Stage 8 — Log
    os.makedirs("logs", exist_ok=True)
    with open("logs/queries.json", "a") as f:
        json.dump({
            "timestamp": time.time(),
            "api_key": x_api_key,
            "role": VALID_API_KEYS[x_api_key],
            "query": request.query,
            "blocked": False,
            "sources": result["sources"],
            "redacted_items": redacted_items,
            "output_leaked": leaked
        }, f)
        f.write("\n")

    return result

@app.get("/", response_class=HTMLResponse)
def interface():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Secure RAG CTI Pipeline</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; background: #f5f5f5; }
            h1 { color: #2c3e50; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box; }
            button { background: #2c3e50; color: white; padding: 12px 30px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            button:hover { background: #34495e; }
            .result { margin-top: 20px; background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #2c3e50; }
            .answer { background: #eafaf1; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .sources { background: #ebf5fb; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .redacted { background: #fdedec; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .cache-badge { background: #f39c12; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
            .blocked { background: #fdedec; padding: 15px; border-radius: 4px; color: #c0392b; }
            h3 { margin-top: 0; color: #2c3e50; }
        </style>
    </head>
    <body>
        <h1>🔒 Secure RAG CTI Pipeline</h1>
        <p>Query MITRE ATT&CK threat intelligence with privacy protection.</p>

        <div class="form-group">
            <label>API Key</label>
            <input type="text" id="apiKey" value="analyst-key-001" />
        </div>

        <div class="form-group">
            <label>Query</label>
            <input type="text" id="query" placeholder="e.g. how does ransomware encrypt files?" />
        </div>

        <div class="form-group">
            <label>Privacy Method</label>
            <select id="privacyMethod">
                <option value="presidio">Presidio (NER-based)</option>
                <option value="regex">Regex (pattern-based)</option>
            </select>
        </div>

        <button onclick="submitQuery()">Submit Query</button>

        <div id="result"></div>

        <script>
    async function submitQuery() {
        const query = document.getElementById('query').value;
        const apiKey = document.getElementById('apiKey').value;
        const privacyMethod = document.getElementById('privacyMethod').value;

        if (!query) {
            alert('Please enter a query');
            return;
        }

        document.getElementById('result').innerHTML = '<p>Loading...</p>';

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': apiKey
                },
                body: JSON.stringify({
                    query: query,
                    privacy_method: privacyMethod
                })
            });

            const data = await response.json();

            if (!response.ok) {
                document.getElementById('result').innerHTML = `
                    <div class="result">
                        <div class="blocked">
                            <h3>Blocked</h3>
                            <p>${data.detail}</p>
                        </div>
                    </div>`;
                return;
            }

            const cacheTag = data.from_cache ? '<span class="cache-badge">FROM CACHE</span>' : '';
            const redactedList = data.redacted_items.length > 0
                ? data.redacted_items.map(r => `<li>${r}</li>`).join('')
                : '<li>Nothing redacted</li>';

            document.getElementById('result').innerHTML = `
                <div class="result">
                    <h3>Results ${cacheTag}</h3>
                    <div class="answer">
                        <h3>Answer</h3>
                        <p>${data.answer.split('\\n').join('<br>')}</p>
                    </div>
                    <div class="sources">
                        <h3>Sources</h3>
                        <ul>${data.sources.map(s => `<li>${s}</li>`).join('')}</ul>
                    </div>
                    <div class="redacted">
                        <h3>Redacted Items</h3>
                        <ul>${redactedList}</ul>
                    </div>
                </div>`;

        } catch (error) {
            document.getElementById('result').innerHTML = `<p>Error: ${error.message}</p>`;
        }
    }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8000)