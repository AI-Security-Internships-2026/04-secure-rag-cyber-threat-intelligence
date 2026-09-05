# Provenance: grounding_eval_100.json

## Purpose

Held-out evaluation set for the ATT&CK output grounding checker (~100 cases).

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
   Short CTI-style answer sentences and evidence paragraphs were written from known MITRE ATT&CK technique themes (encryption, injection, credential dumping, phishing, etc.).  
   They were **not** taken from live LLM RAG outputs of this project.

2. **Technique IDs**  
   - Plausible / irrelevant: standard enterprise ATT&CK IDs (e.g. T1486, T1055, T1003, T1059.001).  
   - Fabricated: IDs that do not exist in ATT&CK (e.g. T9999, T1234.999).  
   - Revoked: **T1086** (historical PowerShell technique, marked revoked in the project snapshot used in earlier tests).

3. **Gold labels**  
   Assigned by fixed rules (human/author rules), **not** by asking an LLM for the label:

   - `REAL_AND_PLAUSIBLE` — ID is real/active; context clearly describes that technique.  
   - `REAL_BUT_IRRELEVANT` — ID is real/active; context describes a **different** behaviour.  
   - `FABRICATED` — ID not in ATT&CK.  
   - `REVOKED` — T1086 with PowerShell-related context.

4. **AI / LLM use**  
   - **No LLM was used to assign gold labels.**  
   - Case strings were drafted programmatically from ATT&CK theme templates for consistency and speed.  
   - If any wording is later edited with an LLM assistant, record model name + prompt in a new dated note under this file; **re-check gold labels manually**.

5. **Threshold**  
   Overlap threshold **0.40** and short-context-first scoring were fixed earlier on fixture/pilot work.  
   **This 100-set is for evaluation only** — do not retune the threshold on it if you report these metrics as test performance.

## How to run

Requires local snapshot:

```text
data/mitre_attack/enterprise_attack_techniques.json
```

```bash
python -m src.benchmark_attack_grounding \
  --labeled experiments/data/grounding_eval_100.json \
  --output experiments/results/attack_grounding_benchmark_100.json
```

## Integrity checks before reporting metrics

- Confirm T1086 is still `revoked: true` in your local snapshot.  
- Spot-check 5 plausible and 5 irrelevant cases: context really matches / mismatches the ID.  
- Confirm fabricated IDs are absent from the snapshot.
