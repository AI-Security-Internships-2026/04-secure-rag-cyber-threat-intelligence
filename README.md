# Secure RAG Pipeline for Cyber Threat Intelligence Sharing

> **CNIT/PNTLab Pisa · TECIP · Scuola Superiore Sant'Anna — AI Security Internship 2026**

---

## Research Problem

Develop a privacy-preserving RAG system that enables organisations to share and query structured threat intelligence (STIX/TAXII) without exposing sensitive indicators in plain text.

---

## Objectives

1. Conduct a systematic literature review on the topic.
2. Design and implement a proof-of-concept prototype.
3. Evaluate the prototype on real or benchmark datasets.
4. Document findings in a final technical report.
5. Present results to the research group.

---

## Expected Deliverables

| Deliverable | Due |
|---|---|
| Literature review (`docs/literature-review.md`) | Week 2 |
| Architecture design document (`docs/proposal.md`) | Week 3 |
| Working prototype (`src/`) | Week 6 |
| Evaluation results (`experiments/results/`) | Week 7 |
| Final report (`docs/final-report.md`) | Week 8 |

---

## Recommended Technology Stack

```
Python, LangChain, STIX2, TAXII2, ChromaDB, FastAPI
```

See `requirements.txt` for pinned dependencies.

---

## Weekly Workflow

```
Monday     – Review weekly tasks in tasks/week-XX.md
Tue–Thu    – Implementation / experiments
Friday     – Document progress in docs/weekly-progress.md
Friday     – Open weekly Pull Request from your branch → dev
```

---

## Branching Policy

| Branch | Purpose |
|---|---|
| `main` | Stable, supervisor-reviewed code only |
| `dev` | Integration branch — merge weekly PRs here |
| `<your-name>-week-XX` | Your working branch for each week |

**Students must never push directly to `main`.**

---

## Pull Request Policy

- One PR per week, targeting the `dev` branch.
- PR title format: `[Week XX] Brief description`
- PR description must reference the weekly task file and summarise what was done.
- A supervisor or co-student must review before merging.

---

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/AI-Security-Internships-2026/04-secure-rag-cyber-threat-intelligence.git
cd 04-secure-rag-cyber-threat-intelligence

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your weekly branch
git checkout dev
git pull origin dev
git checkout -b your-name-week-01

# 5. Run the starter script
python src/main.py
```

---

## Roadmap to September 8, 2026

**Current state:** correct CPU bottleneck profiling, STIX2/TAXII-based MITRE ATT&CK ingestion, and a `docs/guardrail-comparison-mapping.md` already started, mapping components across four guardrail frameworks (issue #6).

**Novel contribution target:** don't just detect prompt injection on the way in — verify that the RAG system's *output* citations (MITRE ATT&CK technique IDs) are actually grounded in real, relevant data, the same pattern that proved valuable in the SOC-guardrails project's CVE-verification work.

| Date | Milestone |
|---|---|
| Aug 2 | Finish `guardrail-comparison-mapping.md`; pick 2 runnable frameworks for real integration |
| Aug 9 | Implement an input guardrail (prompt-injection/malicious query filtering) on the RAG endpoint |
| Aug 16 | Implement an output grounding-check: verify LLM-cited ATT&CK technique IDs actually exist and are relevant, flagging fabricated/ungrounded citations |
| Aug 23 | Benchmark the grounding-check's false-positive/negative rate on a labeled set of real vs. fabricated citations |
| Aug 30 | Full guardrail-comparison write-up (issue #6), integrated into the pipeline |
| Sep 6 | Paper/report draft |
| **Sep 8** | **Final submission** |

---

## Supervisor Note

This repository is managed by **CNIT/PNTLab Pisa, TECIP, Scuola Superiore Sant'Anna**.
Please contact your supervisor before making architectural changes.
All code must be original or properly attributed.
Do **not** commit API keys, passwords, or large datasets — see `.gitignore`.
