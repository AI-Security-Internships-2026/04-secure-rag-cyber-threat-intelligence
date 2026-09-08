# Provenance: adversarial_eval_100.json

## Purpose

100 **adversarial probes** (injection / context-exfil / unredact style) for end-to-end privacy testing.

**Separate from** the 6 hard-coded `ADVERSARIAL_QUERIES` in `src/adversarial_test.py`.

## How created

- Built with **Grok (xAI)** by expanding the original 6 probe patterns into paraphrases/variants.
- Labels are **probe types**, not classifier gold (this is a harness set).
- Gold labels for “blocked vs leaked” come from **running** the pipeline, not from an LLM judge.

## Results path

```text
experiments/results/eval_100/adversarial/
```
