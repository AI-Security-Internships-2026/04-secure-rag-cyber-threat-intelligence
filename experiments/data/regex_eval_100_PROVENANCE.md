# Provenance: regex_eval_100.json

## Purpose

Held-out **privacy redaction / regex accuracy** set (100 texts).

**Separate from:**

- `src/regex_test_set.py` (pilot n=28 hard-coded `TEST_CASES`)
- Legacy `experiments/results/regex_accuracy_results.json`

## Counts by category

| Category | n | Intent |
|----------|---|--------|
| plain | 30 | Clear IPs, domains, emails, hashes, CVEs |
| defanged | 25 | Analyst-style defanging (`[.]`, `(.)`, `hxxp`, etc.) |
| safe | 20 | Whitelisted/public sites — expect **no** redaction |
| trap | 25 | Version strings, filenames, clean CTI prose — FP traps |
| **Total** | **100** | |

## How samples were created

1. **Text** — short CTI-style sentences drafted with **Grok (xAI)** from indicator patterns used in the pilot set, expanded for coverage.  
2. **Gold `expected`** — lists of `[LABEL, exact_substring]` assigned by **fixed rules** (what a correct redactor should extract), **not** by asking an LLM to label spans after the fact.  
3. Includes the original pilot-style cases for continuity plus new plain/defanged/safe/trap examples.  
4. **Not** taken from live `/query` RAG answers.

## Generation rules (effective)

1. Schema: `id`, `category`, `text`, `expected`.  
2. ~100 cases balanced across plain / defanged / safe / trap.  
3. `expected` empty when nothing should be redacted.  
4. Defanged forms keep the **exact** defanged substring in gold (as the pilot set does).  
5. Do not retune regex on this file and report the same file as pure test without a split.

## How to run

```bash
python src/evaluate_regex.py --mode eval100
# or
python src/evaluate_regex.py --labeled experiments/data/regex_eval_100.json \
  --output experiments/results/eval_100/regex/regex_accuracy_results_100.json
```

Default `eval100` mode writes under `experiments/results/eval_100/regex/` and does **not** overwrite `experiments/results/regex_accuracy_results.json`.
