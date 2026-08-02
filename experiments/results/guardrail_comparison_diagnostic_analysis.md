# Guardrail Comparison: Diagnostic Analysis

## Baseline (Keyword-Based)

| Dataset | Precision | Recall | F1 | FP Rate | Avg Latency |
|---|---:|---:|---:|---:|---:|
| CTI Pilot | 100.0% | 66.7% | 80.0% | 0.0% | 0.0118 ms |
| Public Benchmark | 100.0% | 13.3% | 23.5% | 0.0% | 0.0111 ms |

The keyword-based baseline achieved the highest F1-score on the CTI pilot dataset while maintaining perfect precision and zero false positives. This indicates that the detector performs well on known CTI prompt injection patterns.

However, recall dropped from **66.7%** on the CTI pilot set to **13.3%** on the public benchmark. This shows that the keyword-based approach struggles to detect prompt injection attacks that use unseen wording or different phrasing.

---

## LLM Guard (DeBERTa)

| Dataset | Precision | Recall | F1 | FP Rate | Avg Latency |
|---|---:|---:|---:|---:|---:|
| CTI Pilot | 75.0% | 50.0% | 60.0% | 10.0% | 279.8 ms |
| Public Benchmark | 100.0% | 31.7% | 48.1% | 0.0% | 225.4 ms |

LLM Guard improved recall on the public benchmark compared to the keyword baseline (31.7% vs. 13.3%), showing that it can detect a wider range of prompt injection attacks.

However, it performed worse on the CTI pilot dataset. The F1-score decreased from **80.0%** (baseline) to **60.0%**, and one legitimate CTI query, **"password dumping from memory"**, was incorrectly classified as a prompt injection.

This suggests that the model, which was trained on general prompt injection data, may not distinguish between malicious instructions and legitimate cybersecurity terminology. The results indicate a domain mismatch between the training data and CTI-specific queries.

---

## NeMo Guardrails

| Dataset | Precision | Recall | F1 | FP Rate | Avg Latency |
|---|---:|---:|---:|---:|---:|
| CTI Pilot | 0.0% | 0.0% | 0.0% | 0.0% | 1470.5 ms |
| Public Benchmark | 0.0% | 0.0% | 0.0% | 0.0% | 697.2 ms |

NeMo Guardrails failed to detect any prompt injection in either dataset, resulting in zero precision, recall, and F1-score.

Further investigation showed that this was not caused by an implementation error. The evaluated heuristic (`check_jailbreak_length_per_perplexity`) is designed to detect long, low-perplexity jailbreak prompts rather than short conversational prompt injection attacks. As a result, every query was classified as benign.

In addition, NeMo Guardrails had the highest computational cost, with an average latency of **1470.5 ms** and a maximum processing time of **16.3 seconds** on the CTI pilot dataset.

---

## Overall Comparison

| Observation | Finding |
|---|---|
| Best CTI performance | Keyword baseline (F1 = 80.0%) |
| Best public benchmark recall | LLM Guard (31.7%) |
| Lowest latency | Keyword baseline (~0.01 ms) |
| Highest latency | NeMo Guardrails (up to 16.3 s) |
| CTI false positives | LLM Guard (1 false positive) |
| Public benchmark generalization | LLM Guard outperformed the baseline |
| Unsuitable method | NeMo Guardrails heuristic |

The results show a trade-off between domain-specific accuracy and generalization. The keyword-based detector performs best on CTI queries and has the lowest computational cost, but it misses many prompt injections that use unseen wording. LLM Guard improves detection on the public benchmark but introduces additional latency and produced a false positive on a legitimate CTI query, suggesting a domain mismatch. NeMo Guardrails was ineffective for this evaluation because the tested heuristic targets a different class of jailbreak attacks.