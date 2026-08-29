from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import chromadb
import json
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from privacy_filter import is_prompt_injection
from privacy_filter_v2 import redact_with_presidio
from privacy_filter_v3 import redact_sensitive_info 
from llm import generate_response, close_client
from cache import get_cached, set_cache, get_cache_stats
from output_scanner import scan_output
from attack_grounding import check_attack_grounding

app = FastAPI(title="Secure RAG CTI Pipeline")

client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_or_create_collection("mitre_attack")

VALID_API_KEYS = {
    "analyst-key-001": "analyst",
    "analyst-key-002": "analyst",
    "analyst-key-003": "analyst",
    "analyst-key-004": "analyst",
    "analyst-key-005": "analyst",
    "analyst-key-006": "analyst",
    "analyst-key-007": "analyst",
    "analyst-key-008": "analyst",
    "analyst-key-009": "analyst",
    "analyst-key-010": "analyst",
    "admin-key-001": "admin",
    "guest-key-001": "guest"
}

request_counts = {}
RATE_LIMIT = 1000

stats = {
    "total_queries": 0,
    "blocked_queries": 0,
    "cache_hits": 0,
    "output_leaks_caught": 0,
    "ungrounded_citations_caught": 0,
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
    return {"status": "ok", "message": "Secure RAG CTI Pipeline is running"}

@app.get("/stats")
def get_stats(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {
        "total_queries": stats["total_queries"],
        "blocked_queries": stats["blocked_queries"],
        "cache_hits": stats["cache_hits"],
        "output_leaks_caught": stats["output_leaks_caught"],
        "ungrounded_citations_caught": stats["ungrounded_citations_caught"],
        "uptime_seconds": int(time.time() - stats["start_time"]),
        "cache": get_cache_stats()
    }

@app.post("/query")
async def query(request: QueryRequest, x_api_key: str = Header(...)):
    timings = {}
    t_start = time.perf_counter()

    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not check_rate_limit(x_api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    stats["total_queries"] += 1

    # Stage: injection check
    t0 = time.perf_counter()
    injection_flag = is_prompt_injection(request.query)
    timings["injection_check_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    if injection_flag:
        stats["blocked_queries"] += 1
        raise HTTPException(status_code=400, detail="Query blocked: prompt injection detected")

    # Stage: cache check
    t0 = time.perf_counter()
    cached = get_cached(request.query, request.privacy_method)
    timings["cache_check_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    if cached:
        stats["cache_hits"] += 1
        cached = dict(cached)
        cached["from_cache"] = True

        # Re-run cheap grounding on the cached answer (no LLM)
        t0 = time.perf_counter()
        answer_for_check = cached.get("answer") or ""
        grounding = check_attack_grounding(
            answer_for_check,
            cached.get("clean_chunks") or [],
        )
        timings["attack_grounding_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        cached["attack_verifications"] = grounding["verifications"]
        cached["ungrounded_attack_techniques"] = grounding["ungrounded"]
        cached["requires_review"] = grounding["requires_review"]
        cached["grounding_rechecked"] = True

        cached["timings"] = timings
        cached["timings"]["total_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        return cached

    # Stage: retrieval
    t0 = time.perf_counter()
    results = collection.query(query_texts=[request.query], n_results=3)
    timings["retrieval_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage: privacy filter
    t0 = time.perf_counter()
    clean_chunks = []
    redacted_items = []
    for doc in results["documents"][0]:
        if request.privacy_method == "presidio":
            redacted_doc, found = redact_with_presidio(doc)
        else:
            redacted_doc, found = redact_sensitive_info(doc)
        clean_chunks.append(redacted_doc)
        redacted_items.extend(found)
    timings["privacy_filter_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage: LLM generation — the expected bottleneck
    t0 = time.perf_counter()
    answer = await generate_response(request.query, clean_chunks)
    timings["llm_generation_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage: ATT&CK output grounding check
    t0 = time.perf_counter()
    grounding = check_attack_grounding(answer, clean_chunks)
    if grounding["flagged"]:
        stats["ungrounded_citations_caught"] += 1
    # Keep the answer clean — show grounding results separately below
    timings["attack_grounding_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # Stage: output scanner (privacy)
    t0 = time.perf_counter()
    cleaned_answer, leaked_items, leaked = scan_output(answer)
    if leaked:
        stats["output_leaks_caught"] += 1
        redacted_items.extend(leaked_items)
    timings["output_scan_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    timings["total_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

    result = {
        "query": request.query,
        "answer": cleaned_answer,
        "sources": [m["name"] for m in results["metadatas"][0]],
        "redacted_items": redacted_items,
        "attack_verifications": grounding["verifications"],
        "ungrounded_attack_techniques": grounding["ungrounded"],
        "requires_review": grounding["requires_review"],
        "from_cache": False,
        "timings": timings,
        "clean_chunks": clean_chunks,
    }

    set_cache(request.query, request.privacy_method, result)

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
            "output_leaked": leaked,
            "timings": timings,
            "ungrounded_attack_techniques": grounding["ungrounded"],
            "requires_review": grounding["requires_review"],
        }, f)
        f.write("\n")

    return result

@app.on_event("shutdown")
async def shutdown_event():
    await close_client()

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
            input, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box; }
            button { background: #2c3e50; color: white; padding: 12px 30px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            button:hover { background: #34495e; }
            .result { margin-top: 20px; background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #2c3e50; }
            .answer { background: #eafaf1; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .sources { background: #ebf5fb; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .grounding { background: #f5eef8; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .redacted { background: #fdedec; padding: 15px; border-radius: 4px; margin: 10px 0; }
            .timings { background: #fff3cd; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace; }
            .cache-badge { background: #f39c12; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
            .blocked { background: #fdedec; padding: 15px; border-radius: 4px; color: #c0392b; }
            .review-flag { color: #c0392b; font-weight: bold; }
            h3 { margin-top: 0; color: #2c3e50; }
            code { background: #eee; padding: 1px 4px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>Secure RAG CTI Pipeline</h1>
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
        if (!query) { alert('Please enter a query'); return; }
        document.getElementById('result').innerHTML = '<p>Loading...</p>';
        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-api-key': apiKey },
                body: JSON.stringify({ query: query, privacy_method: privacyMethod })
            });
            const data = await response.json();
            if (!response.ok) {
                document.getElementById('result').innerHTML = `<div class="result"><div class="blocked"><h3>Blocked</h3><p>${data.detail}</p></div></div>`;
                return;
            }
            const cacheTag = data.from_cache ? '<span class="cache-badge">FROM CACHE</span>' : '';
            const redactedList = (data.redacted_items && data.redacted_items.length > 0)
                ? data.redacted_items.map(r => `<li>${r}</li>`).join('')
                : '<li>Nothing redacted</li>';
            const timingsHtml = Object.entries(data.timings || {}).map(([k, v]) => `${k}: ${v}ms`).join('<br>');

                        // Grounding section (clean, below the answer)
            const verifications = data.attack_verifications || [];
            let groundingHtml = '';
            if (verifications.length > 0) {
                const plausible = verifications.filter(v => v.classification === 'REAL_AND_PLAUSIBLE');
                const needsReview = verifications.filter(v => v.classification !== 'REAL_AND_PLAUSIBLE');

                const formatItem = (v) => {
                    const name = v.name ? ` (${v.name})` : '';
                    return `<li><code>${v.technique_id}</code> — ${v.classification}${name}</li>`;
                };

                const plausibleHtml = plausible.length > 0
                    ? `<ul>${plausible.map(formatItem).join('')}</ul>`
                    : '';

                const reviewHtml = needsReview.length > 0
                    ? `<p class="review-flag">Requires review</p><ul>${needsReview.map(formatItem).join('')}</ul>`
                    : '';

                const recheckNote = data.grounding_rechecked
                    ? '<p style="font-size:12px;color:#666;">Grounding re-checked on this response</p>'
                    : '';

                groundingHtml = `
                    <div class="grounding">
                        <h3>ATT&amp;CK Grounding Check</h3>
                        ${recheckNote}
                        ${plausibleHtml}
                        ${reviewHtml}
                    </div>`;
            } else {
                groundingHtml = `
                    <div class="grounding">
                        <h3>ATT&amp;CK Grounding Check</h3>
                        <p>No technique IDs found in the answer.</p>
                    </div>`;
            }

            document.getElementById('result').innerHTML = `
                <div class="result">
                    <h3>Results ${cacheTag}</h3>
                    <div class="answer"><h3>Answer</h3><p>${(data.answer || '').split('\\n').join('<br>')}</p></div>
                    ${groundingHtml}
                    <div class="sources"><h3>Sources</h3><ul>${(data.sources || []).map(s => `<li>${s}</li>`).join('')}</ul></div>
                    <div class="redacted"><h3>Redacted Items</h3><ul>${redactedList}</ul></div>
                    <div class="timings"><h3>Timing Breakdown</h3>${timingsHtml}</div>
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)