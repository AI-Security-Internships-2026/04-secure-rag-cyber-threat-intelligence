"""
evaluate_regex.py — Quantitative accuracy comparison: old regex (v1) vs
hardened regex (v3), on a labeled ground-truth test set.

Metric definitions:
  TP (true positive)  = an indicator the regex correctly redacted
  FP (false positive)  = something redacted that shouldn't have been
                          (over-redaction — hurts answer usefulness)
  FN (false negative)  = a real indicator the regex MISSED
                          (privacy leak — the dangerous failure mode)

  Precision = TP / (TP + FP)   -> "of what we redacted, how much was correct"
  Recall    = TP / (TP + FN)   -> "of what should be redacted, how much did we catch"
  F1        = harmonic mean of the two

Modes:
  pilot  — src/regex_test_set.TEST_CASES (n≈28), legacy output path
  eval100 — experiments/data/regex_eval_100.json, output under eval_100/regex/

Usage (from repo root):
    python src/evaluate_regex.py
    python src/evaluate_regex.py --mode eval100
    python src/evaluate_regex.py --mode pilot
    python src/evaluate_regex.py --labeled path.json --output path.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import privacy_filter_v1 as v1
import privacy_filter_v3 as v3

_REPO_ROOT = Path(__file__).resolve().parents[1]

# =============================================================================
# CONFIG
# =============================================================================
EVAL_MODE = "eval100"  # "pilot" | "eval100"

LABELED_PATH_BY_MODE = {
    "eval100": _REPO_ROOT / "experiments" / "data" / "regex_eval_100.json",
    "pilot": None,  # uses regex_test_set.TEST_CASES
}

OUTPUT_PATH_BY_MODE = {
    "pilot": _REPO_ROOT / "experiments" / "results" / "regex_accuracy_results.json",
    "eval100": (
        _REPO_ROOT
        / "experiments"
        / "results"
        / "eval_100"
        / "regex"
        / "regex_accuracy_results_100.json"
    ),
}
# =============================================================================


def load_cases_pilot() -> list[dict]:
    from regex_test_set import TEST_CASES

    cases = []
    for i, c in enumerate(TEST_CASES, 1):
        expected = [(a, b) for a, b in c["expected"]]
        cases.append(
            {
                "id": f"pilot-{i:03d}",
                "category": "pilot",
                "text": c["text"],
                "expected": expected,
            }
        )
    return cases


def load_cases_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for c in data["cases"]:
        expected = [(a, b) for a, b in c["expected"]]
        cases.append(
            {
                "id": c.get("id"),
                "category": c.get("category"),
                "text": c["text"],
                "expected": expected,
            }
        )
    return cases


def score(module, label_name: str, cases: list[dict]) -> dict:
    tp = fp = fn = 0
    per_case = []
    t_start = time.perf_counter()

    for case in cases:
        predicted = set(module.extract_entities(case["text"]))
        expected = set(case["expected"])

        case_tp = predicted & expected
        case_fp = predicted - expected
        case_fn = expected - predicted

        tp += len(case_tp)
        fp += len(case_fp)
        fn += len(case_fn)

        per_case.append(
            {
                "id": case.get("id"),
                "category": case.get("category"),
                "text": case["text"][:70] + ("..." if len(case["text"]) > 70 else ""),
                "true_positives": sorted(list(case_tp)),
                "false_positives": sorted(list(case_fp)),
                "false_negatives": sorted(list(case_fn)),
            }
        )

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "filter_version": label_name,
        "total_test_cases": len(cases),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "eval_time_ms": round(elapsed_ms, 2),
        "per_case_detail": per_case,
    }


def parse_args():
    p = argparse.ArgumentParser(description="Regex v1 vs v3 accuracy evaluation")
    p.add_argument("--mode", choices=["pilot", "eval100"], default=None)
    p.add_argument("--labeled", type=Path, default=None)
    p.add_argument("--output", type=Path, default=None)
    return p.parse_args()


def main():
    args = parse_args()
    mode = args.mode or EVAL_MODE

    if args.labeled:
        cases = load_cases_json(args.labeled)
        labeled_ref = str(args.labeled)
    elif mode == "pilot":
        cases = load_cases_pilot()
        labeled_ref = "src/regex_test_set.TEST_CASES"
    else:
        path = LABELED_PATH_BY_MODE["eval100"]
        if not path.exists():
            raise SystemExit(f"Labeled set not found: {path}")
        cases = load_cases_json(path)
        labeled_ref = str(path)

    output_path = args.output or OUTPUT_PATH_BY_MODE[mode]

    print("=" * 70)
    print("REGEX ACCURACY EVALUATION — v1 (baseline) vs v3 (hardened)")
    print(f"Mode   : {mode}")
    print(f"Labeled: {labeled_ref}  (n={len(cases)})")
    print(f"Output : {output_path}")
    print("=" * 70)

    result_v1 = score(v1, "v1_baseline", cases)
    result_v3 = score(v3, "v3_hardened", cases)

    for r in (result_v1, result_v3):
        print(f"\n--- {r['filter_version']} ---")
        print(f"  Test cases:       {r['total_test_cases']}")
        print(f"  True Positives:   {r['true_positives']}")
        print(f"  False Positives:  {r['false_positives']}  (over-redaction)")
        print(f"  False Negatives:  {r['false_negatives']}  (missed / leaked)")
        print(f"  Precision:        {r['precision']*100:.1f}%")
        print(f"  Recall:           {r['recall']*100:.1f}%")
        print(f"  F1 Score:         {r['f1_score']*100:.1f}%")
        print(f"  Eval time:        {r['eval_time_ms']}ms")

    print("\n" + "=" * 70)
    print("SUMMARY — improvement (v3 - v1)")
    print("=" * 70)
    print(f"  Recall improvement:    {(result_v3['recall']-result_v1['recall'])*100:+.1f} points")
    print(f"  Precision change:      {(result_v3['precision']-result_v1['precision'])*100:+.1f} points")
    print(f"  F1 improvement:        {(result_v3['f1_score']-result_v1['f1_score'])*100:+.1f} points")
    print("=" * 70)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "test_date": time.strftime("%Y-%m-%d"),
                "mode": mode,
                "labeled_set": labeled_ref,
                "v1_baseline": {k: v for k, v in result_v1.items() if k != "per_case_detail"},
                "v3_hardened": {k: v for k, v in result_v3.items() if k != "per_case_detail"},
                "v1_detail": result_v1["per_case_detail"],
                "v3_detail": result_v3["per_case_detail"],
            },
            f,
            indent=2,
        )
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()