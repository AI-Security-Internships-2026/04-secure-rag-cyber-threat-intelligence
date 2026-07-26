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

Run: python3 evaluate_regex.py
"""
import json
import os
import time
import privacy_filter_v1 as v1
import privacy_filter_v3 as v3
from regex_test_set import TEST_CASES


def score(module, label_name: str) -> dict:
    tp, fp, fn = 0, 0, 0
    per_case = []
    t_start = time.perf_counter()

    for case in TEST_CASES:
        predicted = set(module.extract_entities(case["text"]))
        expected = set(case["expected"])

        case_tp = predicted & expected
        case_fp = predicted - expected
        case_fn = expected - predicted

        tp += len(case_tp)
        fp += len(case_fp)
        fn += len(case_fn)

        per_case.append({
            "text": case["text"][:70] + ("..." if len(case["text"]) > 70 else ""),
            "true_positives": sorted(list(case_tp)),
            "false_positives": sorted(list(case_fp)),
            "false_negatives": sorted(list(case_fn)),
        })

    elapsed_ms = (time.perf_counter() - t_start) * 1000

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "filter_version": label_name,
        "total_test_cases": len(TEST_CASES),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "eval_time_ms": round(elapsed_ms, 2),
        "per_case_detail": per_case,
    }


def main():
    print("=" * 70)
    print("REGEX ACCURACY EVALUATION — v1 (baseline) vs v3 (hardened)")
    print("=" * 70)

    result_v1 = score(v1, "v1_baseline")
    result_v3 = score(v3, "v3_hardened")

    for r in (result_v1, result_v3):
        print(f"\n--- {r['filter_version']} ---")
        print(f"  Test cases:       {r['total_test_cases']}")
        print(f"  True Positives:   {r['true_positives']}")
        print(f"  False Positives:  {r['false_positives']}  (over-redaction)")
        print(f"  False Negatives:  {r['false_negatives']}  (missed / leaked)")
        print(f"  Precision:        {r['precision']*100:.1f}%")
        print(f"  Recall:           {r['recall']*100:.1f}%")
        print(f"  F1 Score:         {r['f1_score']*100:.1f}%")
        print(f"  Eval time:        {r['eval_time_ms']}ms for {r['total_test_cases']} cases")

    print("\n" + "=" * 70)
    print("SUMMARY — improvement")
    print("=" * 70)
    print(f"  Recall improvement:    {(result_v3['recall']-result_v1['recall'])*100:+.1f} points")
    print(f"  Precision change:      {(result_v3['precision']-result_v1['precision'])*100:+.1f} points")
    print(f"  F1 improvement:        {(result_v3['f1_score']-result_v1['f1_score'])*100:+.1f} points")
    print("=" * 70)

    # print detailed misses so you can see exactly what each version got wrong
    for r in (result_v1, result_v3):
        misses = [c for c in r["per_case_detail"] if c["false_negatives"] or c["false_positives"]]
        if misses:
            print(f"\n--- {r['filter_version']} — cases with errors ---")
            for c in misses:
                print(f"  TEXT: {c['text']}")
                if c["false_negatives"]:
                    print(f"    MISSED (leak risk): {c['false_negatives']}")
                if c["false_positives"]:
                    print(f"    OVER-REDACTED:      {c['false_positives']}")

    output = {
        "test_date": time.strftime("%Y-%m-%d"),
        "v1_baseline": {k: v for k, v in result_v1.items() if k != "per_case_detail"},
        "v3_hardened": {k: v for k, v in result_v3.items() if k != "per_case_detail"},
        "v1_detail": result_v1["per_case_detail"],
        "v3_detail": result_v3["per_case_detail"],
    }
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experiments", "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "regex_accuracy_results.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()