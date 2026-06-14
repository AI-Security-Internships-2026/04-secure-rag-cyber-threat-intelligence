# Literature Review: Secure RAG Pipeline for Cyber Threat Intelligence Sharing

**Student:** Maria Mahmood

**Updated:** 14-06-2026

---

## Instructions

For each paper or resource you read, complete one entry below.
Aim for at least **10 papers** by the end of Week 2.
Use Google Scholar, IEEE Xplore, ACM DL, arXiv, or USENIX Security.

---

<!-- ## Paper Summary Template

### Paper N — [Short Title]

| Field | Content |
|---|---|
| **Full title** | |
| **Authors** | |
| **Year** | |
| **Venue** | (Conference / Journal / arXiv) |
| **URL / DOI** | |
| **Method** | (brief description of the approach) |
| **Dataset** | (what data was used) |
| **Key result** | (main finding or metric) |
| **Limitation** | (what the paper does not address) |
| **Relevance to our project** | (why this matters for us) |

**Notes / Quotes:**
> _Paste important quotes or your personal notes here._

---

## Reference Table (Quick Overview)

| # | Title (short) | Authors | Year | Method | Dataset | Relevance |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

---

## Tools and Datasets Identified

| Name | Type | URL | Notes |
|---|---|---|---|
| | Dataset | | |
| | Library / Tool | | | -->


## Relevant Resources Summary

### Resource 1 — OpenCTI (Real-World Cyber Threat Intelligence Platform)

| Field | Content |
|---|---|
| **Full title** | Open Cyber Threat Intelligence Platform |
| **Authors** | Filigran |
| **Year** | Ongoing |
| **Venue** | GitHub / Production System |
| **URL / DOI** | https://github.com/OpenCTI-Platform/opencti |
| **Method** | STIX/TAXII-based CTI ingestion, enrichment, storage, and sharing |
| **Dataset** | Real-world threat intelligence feeds (STIX objects) |
| **Key result** | Production-grade CTI platform used by security organizations |
| **Limitation** | Does not include LLM-based retrieval or RAG integration |
| **Relevance to our project** | Serves as the architectural reference for CTI pipeline design |

**Notes / Quotes:**
> OpenCTI is one of the most widely used open-source platforms for cyber threat intelligence management.

---

### Resource 2 — STIX2 Python Library (Core CTI Implementation Tool)

| Field | Content |
|---|---|
| **Full title** | STIX 2 Python Library |
| **Authors** | OASIS CTI Working Group |
| **Year** | Ongoing |
| **Venue** | GitHub |
| **URL / DOI** | https://github.com/oasis-open/cti-python-stix2 |
| **Method** | Python SDK for creating, parsing, and validating STIX 2.1 objects |
| **Dataset** | Structured CTI data (STIX format) |
| **Key result** | Enables programmatic handling of threat intelligence data |
| **Limitation** | No retrieval or AI integration capabilities |
| **Relevance to our project** | Core dependency for converting CTI into structured RAG inputs |

**Notes / Quotes:**
> Provides the official Python implementation of the STIX 2.1 specification.

---

### Resource 3 — MITRE ATT&CK Framework (Threat Intelligence Dataset)

| Field | Content |
|---|---|
| **Full title** | MITRE ATT&CK Framework |
| **Authors** | MITRE Corporation |
| **Year** | Ongoing |
| **Venue** | Industry Knowledge Base |
| **URL / DOI** | https://attack.mitre.org |
| **Method** | Structured knowledge base of adversary tactics, techniques, and procedures |
| **Dataset** | Cyberattack behavior dataset |
| **Key result** | Standard global taxonomy for threat intelligence |
| **Limitation** | Not designed for machine learning or retrieval systems |
| **Relevance to our project** | Provides evaluation dataset and structured CTI knowledge |

**Notes / Quotes:**
> ATT&CK is widely used as the standard for adversary behavior modeling in cybersecurity.

---

### Resource 4 — SD-RAG (Secure Retrieval-Augmented Generation)

| Field | Content |
|---|---|
| **Full title** | SD-RAG: Selective Disclosure in Retrieval-Augmented Generation |
| **Authors** | Research Authors |
| **Year** | 2026 |
| **Venue** | arXiv |
| **URL / DOI** | https://arxiv.org/abs/2601.11199 |
| **Method** | Retrieval-time filtering and selective disclosure before LLM input |
| **Dataset** | RAG benchmark datasets |
| **Key result** | Reduces prompt injection and sensitive data leakage in RAG systems |
| **Limitation** | Not specialized for cyber threat intelligence use cases |
| **Relevance to our project** | Direct theoretical foundation for secure RAG design |

**Notes / Quotes:**
> Focuses on controlling what information is revealed to the LLM during retrieval.

---

### Resource 5 — RAG Poisoning Attack (Implementation + Code Base)

| Field | Content |
|---|---|
| **Full title** | RAG Poisoning Attack Proof-of-Concept |
| **Authors** | Prompt Security |
| **Year** | 2025 |
| **Venue** | GitHub Project |
| **URL / DOI** | https://github.com/prompt-security/RAG_Poisoning_POC |
| **Method** | Injecting malicious documents into vector databases to manipulate retrieval |
| **Dataset** | Synthetic poisoned documents + embeddings |
| **Key result** | Demonstrates vulnerability of embedding-based retrieval systems |
| **Limitation** | Focused on attack simulation only, not defenses |
| **Relevance to our project** | Defines threat model for secure RAG pipeline |

**Notes / Quotes:**
> Shows how vector databases can be manipulated through adversarial document injection.

---

### Resource 6 — Secure RAG Risk & Architecture Framework

| Field | Content |
|---|---|
| **Full title** | Securing Retrieval-Augmented Generation: Risk Assessment Framework |
| **Authors** | Research Authors |
| **Year** | 2025 |
| **Venue** | arXiv |
| **URL / DOI** | https://arxiv.org/abs/2505.08728 |
| **Method** | System-level breakdown of RAG security vulnerabilities and mitigations |
| **Dataset** | Multiple RAG system benchmarks |
| **Key result** | Defines attack surfaces in retrieval, embedding, and generation layers |
| **Limitation** | Does not include full implementation code |
| **Relevance to our project** | Helps design secure architecture and evaluation strategy |

**Notes / Quotes:**
> Breaks RAG systems into distinct attack surfaces for structured security analysis.

---

## Reference Table (Quick Overview)

| # | Title (short) | Authors | Year | Method | Dataset | Relevance |
|---|---|---|---|---|---|---|
| 1 | OpenCTI | Filigran | Ongoing | CTI Platform | STIX feeds | Real-world architecture |
| 2 | STIX2 Library | OASIS | Ongoing | CTI SDK | STIX objects | Data processing |
| 3 | MITRE ATT&CK | MITRE | Ongoing | Knowledge base | Attack techniques | Evaluation dataset |
| 4 | SD-RAG | Research | 2026 | Secure RAG design | Benchmarks | Privacy filtering |
| 5 | RAG Poisoning POC | Prompt Security | 2025 | Attack simulation | Embeddings | Threat model |
| 6 | Secure RAG Framework | Research | 2025 | System security analysis | RAG systems | Architecture design |

---

## Tools and Datasets Identified

| Name | Type | URL | Notes |
|---|---|---|---|
| OpenCTI | Platform | https://github.com/OpenCTI-Platform/opencti | Full CTI system |
| STIX2 | Library | https://github.com/oasis-open/cti-python-stix2 | CTI data handling |
| MITRE ATT&CK | Dataset | https://attack.mitre.org | Threat intelligence dataset |
| LangChain | Framework | https://github.com/langchain-ai/langchain | RAG pipeline builder |
| ChromaDB | Vector DB | https://github.com/chroma-core/chroma | Embedding storage |
| RAG Poisoning POC | Security Tool | https://github.com/prompt-security/RAG_Poisoning_POC | Attack simulation |

---

## Summary

This literature review focuses on **real systems, implementation frameworks, and security-focused RAG research**.

The selected resources collectively support:
- Building a CTI ingestion pipeline (OpenCTI, STIX2)
- Using standard threat intelligence datasets (MITRE ATT&CK)
- Implementing RAG systems (LangChain, ChromaDB)
- Understanding attack surfaces (RAG poisoning)
- Designing secure architectures (SD-RAG, security framework papers)

This directly supports the development of a **production-style Secure RAG system for Cyber Threat Intelligence sharing**.
