# Research Proposal: Secure RAG Pipeline for Cyber Threat Intelligence Sharing

**Student:** Maria Mahmood <br>
**Supervisor:** Dr. Rana Abu Bakar <br>
**Start date:** June 2026 <br>
**Expected end date:** August 2026 <br>

---

## 1. Background

Develop a privacy-preserving RAG system that enables organisations to share and query structured threat intelligence (STIX/TAXII) without exposing sensitive indicators in plain text.

This project is carried out within the AI Security research agenda of CNIT/PNTLab Pisa (TECIP, Scuola Superiore Sant'Anna).

---

## 2. Problem Statement

Organisations that share cyber threat intelligence (CTI) face a fundamental tension, that is sharing detailed threat indicators improves collective defence, but exposing raw indicators such as IP addresses, file hashes, and domain names creates privacy and operational security risks. 

Existing platforms like OpenCTI and TAXII servers share intelligence in plain STIX format with no semantic query capability or privacy filtering. Large language models offer powerful retrieval and summarisation capabilities, but standard RAG pipelines expose all retrieved content directly to the model, making them vulnerable to prompt injection and sensitive data leakage. 

There is currently no production-ready system that combines STIX/TAXII-based threat intelligence retrieval with privacy-preserving generation. This project addresses that gap by designing and evaluating a secure RAG pipeline for CTI sharing.

---

## 3. Research Questions

1. _RQ1:_ How can STIX/TAXII threat intelligence objects be effectively ingested and retrieved using a vector-based RAG pipeline?
2. _RQ2:_ Which privacy-preserving mechanisms best reduce sensitive indicator leakage without significantly degrading response quality?
3. _RQ3:_ How does the proposed secure RAG system perform compared to a standard RAG baseline in terms of retrieval accuracy, answer faithfulness, and privacy protection?

---

## 4. Proposed Methodology

### 4.1 Data Collection / Dataset

The primary dataset will be MITRE ATT&CK threat intelligence objects, accessed via the STIX2 Python library. Additional threat intelligence will be sourced from AlienVault OTX in STIX format. Both sources are publicly available and do not require special access.

### 4.2 Approach

The system will follow a three-stage pipeline:
1. **Ingestion** — STIX/TAXII threat intelligence objects are parsed using the stix2 Python library and converted into text chunks.
2. **Retrieval** — Chunks are embedded and stored in ChromaDB. Queries are matched using semantic similarity search.
3. **Privacy-Preserving Generation** — Before retrieved chunks reach the LLM, sensitive indicators (IPs, hashes, domain names) are filtered or anonymized using a selective disclosure mechanism inspired by SD-RAG (2026).

### 4.3 Evaluation Metrics

- Retrieval accuracy (Recall@K)
- Answer faithfulness (BERTScore)
- Privacy leakage rate (% of sensitive indicators exposed in output)

### 4.4 Tooling

- stix2, taxii2-client — CTI data handling
- LangChain — RAG pipeline
- ChromaDB — vector store
- FastAPI — query API layer
- Python 3.11, Conda environment

---

## 5. Expected Outcome

The primary deliverable is a working prototype of a secure RAG pipeline that ingests STIX/TAXII threat intelligence, stores embeddings in ChromaDB, and generates responses with privacy-filtered context. The system will be evaluated on retrieval accuracy, answer faithfulness, and privacy leakage rate. A final technical report documenting the architecture, implementation, and evaluation results will also be produced.

---

## 6. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Dataset not publicly available | Medium | Use synthetic data or reach out to CNIT partners |
| Compute resources insufficient | Low | Use university HPC cluster |
| Scope too broad | High | Focus on one sub-problem; extend if time allows |

---

_Last updated: 2026-06-20_
