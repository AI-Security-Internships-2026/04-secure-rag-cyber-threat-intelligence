# Guardrail Comparison: Component Mapping

**Student:** Maria Mahmood <br>
**Week:** 6 <br>
**Related task:** Compare the repository's current LLM security control against
technically equivalent components in open-source guardrail frameworks.

---

## 1. Security task being evaluated

Binary classification of a user query as **prompt injection / jailbreak attempt**
vs **benign query**, applied **before retrieval** — the same point in the pipeline
as `privacy_filter.py::is_prompt_injection()`.

## 2. Current repo control

- **Files:** `src/privacy_filter.py`, `src/privacy_filter_v2.py`
- **Method:** keyword/substring matching against a fixed list of injection
  signatures (e.g. `"ignore previous instructions"`, `"repeat the exact"`,
  `"you are now"`)
- No ML model, no external dependency, effectively 0ms latency

## 3. Comparable component identified in each framework

| Framework | Component | Detection method | Runs fully offline / no auth? | Source |
|---|---|---|---|---|
| Protect AI LLM Guard | `input_scanners.PromptInjection` | Fine-tuned DeBERTa-v3 classifier (`ProtectAI/deberta-v3-base-prompt-injection-v2`), binary label + risk score | Yes — `pip install llm-guard`, no API key | https://github.com/protectai/llm-guard/blob/main/docs/input_scanners/prompt_injection.md |
| NVIDIA NeMo Guardrails | `jailbreak detection heuristics` input rail | Statistical heuristic: length/perplexity + prefix-suffix perplexity, computed via GPT-2-large, in-process | Yes — no API key for in-process mode | https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/jailbreak-protection |
| NVIDIA NeMo Guardrails (secondary rail, not used in this pass) | `self check input` | LLM-as-judge — asks the main LLM to classify the query against a policy prompt | Needs an LLM call | https://docs.nvidia.com/nemo/guardrails/getting_started/4_input_rails/README.html |
| Guardrails AI | `hub://guardrails/detect_jailbreak` (`DetectJailbreak`) | Local classifier, score 0.0 (safe) -> 1.0 (jailbreak), configurable threshold | Model runs locally, but `guardrails hub install` needs a one-time free Guardrails Hub account/token | https://github.com/guardrails-ai/detect_jailbreak |
| Meta LlamaFirewall | `PromptGuard 2` scanner | Fine-tuned DeBERTa/mDeBERTa classifier (22M/86M params), binary jailbreak score | Model hosted on HuggingFace; `llamafirewall configure` may require HF login for gated weights | https://meta-llama.github.io/PurpleLlama/LlamaFirewall/docs/documentation/scanners/prompt-guard-2 |

All four map to the same function as the repo's control, so none are technically
incompatible. The only real constraint is auth/download friction.

## 4. Selected for this benchmark pass (fully local, no auth)

1. `current_repo` — baseline (`is_prompt_injection`)
2. `llm_guard.PromptInjection`
3. NeMo Guardrails jailbreak-detection heuristics

## 5. Deferred to a later pass (documented reason, not incompatibility)

- **Guardrails AI `DetectJailbreak`** — needs a one-time free Guardrails Hub
  account/token for `guardrails hub install`. Will add once configured.
- **Meta LlamaFirewall `PromptGuard 2`** — model weights are gated on
  HuggingFace and require account approval via `llamafirewall configure`.
  Will add once access is granted.

## 6. Evaluation dataset

Pilot set (n=16), reused from existing repo test data — no per-framework tuning:

- **Positive class (label=1), n=6:** `src/adversarial_test.py::ADVERSARIAL_QUERIES`
- **Negative class (label=0), n=10:** `src/evaluate_manual.py::TEST_QUERIES`

This is pilot-sized only and will be expanded before the final report.

## 7. Reproduction

```bash
pip install llm-guard "nemoguardrails[jailbreak]" transformers torch
python src/guardrail_eval.py
```

Results are written to `experiments/results/guardrail_comparison.json`.