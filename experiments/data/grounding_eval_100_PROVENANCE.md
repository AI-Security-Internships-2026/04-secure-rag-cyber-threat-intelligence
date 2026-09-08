# Provenance: grounding_eval_100.json

## Purpose

Held-out evaluation set for the ATT&CK output grounding checker (100 cases).

**Separate from:**

- `tests/fixtures/attack_techniques_fixture.json` (mini unit-test fixture)
- `experiments/data/grounding_labeled_set.json` (pilot n≈20)

## Counts

| Gold class | n |
|------------|---|
| REAL_AND_PLAUSIBLE | 32 |
| REAL_BUT_IRRELEVANT | 28 |
| FABRICATED | 28 |
| REVOKED | 12 |
| **Total cases** | **100** |

## How samples were created

1. **Answer + retrieved_context text**  
   Short CTI-style answer sentences and evidence paragraphs were drafted with assistance from **Grok (xAI)** from known MITRE ATT&CK technique themes (encryption, injection, credential dumping, phishing, lateral movement, etc.).  
   They were **not** taken from live LLM RAG outputs of this project.

2. **Technique IDs**  
   - Plausible / irrelevant: standard enterprise ATT&CK IDs (e.g. T1486, T1055, T1003, T1059.001).  
   - Fabricated: IDs that do not exist in ATT&CK (e.g. T9999, T1234.999).  
   - Revoked: **T1086** (historical PowerShell technique, marked revoked in the project snapshot used in earlier tests).

3. **Gold labels**  
   Assigned by fixed rules (author-defined rules), **not** by asking an LLM to classify each case:

   - `REAL_AND_PLAUSIBLE` — ID is real/active; context clearly describes that technique.  
   - `REAL_BUT_IRRELEVANT` — ID is real/active; context describes a **different** behaviour.  
   - `FABRICATED` — ID not in ATT&CK.  
   - `REVOKED` — T1086 with PowerShell-related context.

4. **AI / LLM use**  
   - **Tool:** Grok (xAI), in a project chat used to build the evaluation set.  
   - **Gold labels:** assigned by the fixed rules in §3, **not** by an LLM classifier.  
   - **Answer and retrieved_context text:** drafted in one structured generation pass (see **Prompts / generation instructions** below), then stored in `grounding_eval_100.json`.  
   - **Human responsibility:** author owns class balance and label rules; spot-check real / irrelevant / fabricated IDs against the local ATT&CK snapshot before reporting metrics.  
   - No ChatGPT / Claude / Groq model was used as a **labeler**. No live outputs from this project's RAG endpoint were used as evaluation cases.

5. **Threshold**  
   Overlap threshold **0.40** and short-context-first scoring were fixed earlier on fixture/pilot work.  
   **This 100-set is for evaluation only** — do not retune the threshold on it if you report these metrics as test performance.

## Prompts / generation instructions

### What was *not* done

- No per-case prompt of the form: “Classify this citation as FABRICATED / …”  
- No sampling of answers from the project’s live `/query` RAG endpoint  
- No unlabeled LLM free-write of 100 cases without class rules  

### Generation rules applied by Grok (effective system-style instructions)

When drafting each case, the following constraints were applied:

1. Output JSON cases with fields: `id`, `answer`, `retrieved_context`, `gold`.  
2. Target about 100 cases with approximate balance:  
   - REAL_AND_PLAUSIBLE ≈ 30–35  
   - REAL_BUT_IRRELEVANT ≈ 25–30  
   - FABRICATED ≈ 25–30  
   - REVOKED ≈ 5–12  
3. For **REAL_AND_PLAUSIBLE**: choose a real ATT&CK technique ID; write a short answer that cites that ID; write retrieved context that clearly describes the **same** technique.  
4. For **REAL_BUT_IRRELEVANT**: choose a real ATT&CK technique ID; write an answer that cites that ID; write retrieved context about a **different** behaviour so the ID is unsupported by evidence.  
5. For **FABRICATED**: invent non-existent IDs (e.g. T9999, T1234.999); context may be generic CTI text.  
6. For **REVOKED**: use **T1086** (revoked PowerShell technique in the project snapshot) with PowerShell-related context.  
7. Do **not** assign labels by model judgment alone; labels must follow rules 3–6.  
8. Keep answers and contexts short, analyst/CTI-style English.  
9. Do not use live outputs from the secure RAG demo as cases.

### Example of the case pattern (not a separate API call)

**Plausible pattern**

- Answer: cite real ID + correct behaviour name  
- Context: paraphrase of that technique’s idea (encryption / injection / credential dumping / …)  
- Gold: `{ "Txxxx": "REAL_AND_PLAUSIBLE" }`

**Irrelevant pattern**

- Answer: cite real ID  
- Context: clearly different behaviour (e.g. cite T1486 but context only about phishing)  
- Gold: `{ "Txxxx": "REAL_BUT_IRRELEVANT" }`

**Fabricated pattern**

- Answer: cite fake ID  
- Gold: `{ "T9xxx": "FABRICATED" }`

**Revoked pattern**

- Answer: cite T1086  
- Context: PowerShell-related  
- Gold: `{ "T1086": "REVOKED" }`

Cases were produced in batch under those rules.

## Benchmark result (recorded)

Command:

```bash
python -m src.benchmark_attack_grounding \
  --labeled experiments/data/grounding_eval_100.json \
  --output experiments/results/attack_grounding_benchmark_100.json