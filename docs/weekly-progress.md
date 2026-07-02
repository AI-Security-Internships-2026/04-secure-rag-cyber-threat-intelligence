# Weekly Progress Log: Secure RAG Pipeline for Cyber Threat Intelligence Sharing

**Student:** Maria Mahmood

**GitHub username:** MariaMahmood18

---

## How to Use This File

Add a new section every Friday before opening your weekly Pull Request.
Be honest — problems and blockers are normal and help your supervisor support you.

---

## Week 1

**Branch:** `maria-week-01`

**PR link:** https://github.com/AI-Security-Internships-2026/04-secure-rag-cyber-threat-intelligence/pull/1

### Completed this week
- [x] Read README and proposal
- [x] Set up local environment (Python venv, dependencies)
- [x] Ran `src/main.py` successfully
- [x] Wrote personal introduction (below)
- [x] Identified 5 related papers / tools / datasets
- [x] Expanded literature review to 10 resources covering CTI tools, RAG frameworks, and security standards

### Personal Introduction
My name is Maria Mahmood, currently I'm pursuing MS in Artificial Intelligence at NUST, Islamabad. 
I have hands-on experience in Python, TensorFlow, PyTorch, and have previously built a 
RAG-based pipeline for radiology report summarization under OCR noise. Through this internship, 
I hope to extend my RAG knowledge into cybersecurity — learning how STIX/TAXII threat intelligence 
is processed and how privacy-preserving techniques apply to intelligence sharing systems.

### Problems / Blockers
No major blockers this week.

### Next week plan
- Read the 5 papers identified this week
- Complete `docs/proposal.md` draft
- Set up dataset download / preprocessing pipeline

---

## Week 2

**Branch:** `maria-week-02`
**PR link:** https://github.com/AI-Security-Internships-2026/04-secure-rag-cyber-threat-intelligence/pull/2

### Completed this week
- [x] Uncommented Week 2 templates in weekly-progress.md and literature-review.md
- [x] Read SD-RAG paper in detail and added structured notes to literature review
- [x] Added DOIs for Resource 4 (SD-RAG) and Resource 6 (Secure RAG Framework)
- [x] Installed and tested STIX2 library with a MITRE ATT&CK style object
- [x] Installed and tested ChromaDB with a sample CTI document
- [x] Drafted docs/proposal.md Sections 2, 3, 4 and 5

### Problems / Blockers
No major blockers this week.

### Next week plan
- Begin implementing the ingestion pipeline in src/
- Connect STIX2 parser to ChromaDB embeddings
- Test end-to-end retrieval with sample CTI data

---

## Week 3

**Branch:** `maria-week-03`
**PR link:** https://github.com/AI-Security-Internships-2026/04-secure-rag-cyber-threat-intelligence/pull/3

### Completed this week
- [x] Downloaded real MITRE ATT&CK STIX bundle (858 attack techniques)
- [x] Built ingestion pipeline (`src/ingest.py`) to parse and load STIX objects into ChromaDB
- [x] Built semantic query script (`src/query.py`) and verified correct results using vector search
- [x] Built regex-based privacy filter (`src/privacy_filter.py`) to redact IPs, hashes, domains, emails and CVEs
- [x] Upgraded privacy filter (`src/privacy_filter_v2.py`) using Microsoft Presidio for NER-based detection of person names, emails, IPs and URLs
- [x] Added domain whitelist to both filters to prevent false positives on public reference URLs like attack.mitre.org
- [x] Added prompt injection detection to block malicious queries before they reach ChromaDB
- [x] Built unified pipeline (`src/pipeline.py`) supporting both regex and Presidio privacy methods
- [x] Documented MITRE ATT&CK dataset in `datasets/mitre-attack.md`
- [x] Added Presidio and spaCy to `requirements.txt`

### Problems / Blockers
Regex filter was initially flagging `attack.mitre.org` as a sensitive domain — a false positive. Solved by adding a whitelist of known safe public domains to both privacy filters.

### Next week plan
- Explore and improve privacy filtering in more depth — evaluate both regex and Presidio methods against more complex CTI data
- Study and plan scalability approach — how to handle multiple concurrent users with no GPU
- Research rate limiting and authentication strategies for the proxy layer
- Begin wrapping the pipeline in FastAPI for multi-user query handling

---

## Week 4

**Branch:** `maria-week-04`
**PR link:** https://github.com/AI-Security-Internships-2026/04-secure-rag-cyber-threat-intelligence/pull/4

### Completed this week
- [x] Designed 10 test queries covering different MITRE ATT&CK attack categories
- [x] Built manual evaluation script (`src/evaluate_manual.py`) with human relevance judgment
- [x] Built automatic evaluation script (`src/evaluate_auto.py`) using exact name matching
- [x] Built combo evaluation script (`src/evaluate_auto_v2.py`) combining exact and semantic matching
- [x] Manual Precision@3: 78.3%
- [x] Automatic Precision@3: 30.0%
- [x] Combined Precision@3: 36.7%
- [x] Identified incomplete ground truth problem explaining gap between manual and automatic scores
- [x] Saved all evaluation results to experiments/results/

### Problems / Blockers
Gap between manual (78.3%) and automatic (36.7%) precision reveals incomplete ground truth problem, predefined expected technique names don't cover all valid answers the pipeline returns.

### Next week plan
- Integrate Groq Cloud LLM API to complete RAG pipeline with actual response generation
- Build FastAPI wrapper with /query, /health and /stats endpoints
- Add API key authentication and role based access control
- Add rate limiting per user
- Add query logging for auditing

---

_(Add a new section each week)_
