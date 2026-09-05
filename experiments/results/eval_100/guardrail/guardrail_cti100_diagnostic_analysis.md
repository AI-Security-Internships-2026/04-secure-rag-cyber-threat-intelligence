# Guardrail Comparison Summary — 2026-09-05

CTI set: 45 positive + 55 negative (mode=cti100)
Public benchmark: 116 examples (deepset/prompt-injections (test split))

## CTI set (domain-specific)

| Method | Precision | Recall | F1 | FP Rate | Avg Latency |
|---|---|---|---|---|---|
| Baseline (keyword) | 100.0% | 13.3% | 23.5% | 0.0% | 0.0035ms |
| LLM Guard (DeBERTa) | 96.5% | 62.2% | 75.7% | 1.8% | 105.5507ms |
| NeMo Guardrails (GPT2 heuristic) | 0.0% | 0.0% | 0.0% | 0.0% | 441.4382ms |

## Public Benchmark (general-purpose)

| Method | Precision | Recall | F1 | FP Rate | Avg Latency |
|---|---|---|---|---|---|
| Baseline (keyword) | 100.0% | 13.3% | 23.5% | 0.0% | 0.0037ms |
| LLM Guard (DeBERTa) | 100.0% | 31.7% | 48.1% | 0.0% | 103.9935ms |
| NeMo Guardrails (GPT2 heuristic) | 0.0% | 0.0% | 0.0% | 0.0% | 470.8183ms |