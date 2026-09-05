"""
Benchmark ATT&CK output grounding check.

Measures false-positive and false-negative rates on a labeled set of
real vs fabricated (and irrelevant / revoked) citations.

Definition used for binary metrics
----------------------------------
Positive class = "should be flagged as ungrounded"
  gold in {FABRICATED, REVOKED, REAL_BUT_IRRELEVANT}

Negative class = "should pass as grounded"
  gold == REAL_AND_PLAUSIBLE

Prediction positive = checker classification != REAL_AND_PLAUSIBLE
Prediction negative = checker classification == REAL_AND_PLAUSIBLE

Also reports per-class agreement (exact classification match).

Usage:
    python -m src.benchmark_attack_grounding
    python -m src.benchmark_attack_grounding --threshold 0.40
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from attack_grounding import (  
    OVERLAP_THRESHOLD,
    check_attack_grounding,
    verify_technique,
)

DEFAULT_LABELED = ROOT / "experiments" / "data" / "grounding_labeled_set.json"
DEFAULT_OUT = ROOT / "experiments" / "results" / "attack_grounding_benchmark.json"

# Binary: should the citation be flagged?
SHOULD_FLAG = {"FABRICATED", "REVOKED", "REAL_BUT_IRRELEVANT"}
SHOULD_PASS = {"REAL_AND_PLAUSIBLE"}


def load_cases(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


def safe_div(n: float, d: float) -> float:
    return round(n / d, 4) if d else 0.0


def evaluate_case(case: dict, threshold: float) -> list[dict]:
    """Run checker on one case; return per-ID records."""
    answer = case["answer"]
    context = case["retrieved_context"]
    gold_map = case["gold"]

    # Full pipeline path (same as production entry point)
    result = check_attack_grounding(answer, [context])
    pred_by_id = {v["technique_id"]: v for v in result["verifications"]}

    rows = []
    for tid, gold in gold_map.items():
        pred_info = pred_by_id.get(tid)
        if pred_info is None:
            pred_cls = "MISSING"
            overlap = None
            pred_flag = False   # checker did NOT fire
        else:
            pred_cls = pred_info["classification"]
            overlap = pred_info.get("topical_overlap")
            pred_flag = pred_cls != "REAL_AND_PLAUSIBLE"

        gold_flag = gold in SHOULD_FLAG  # FABRICATED / REVOKED / REAL_BUT_IRRELEVANT

        if pred_cls == "MISSING":
            # Missed extraction of a gold ID: FN if it should have been flagged
            binary = "FN" if gold_flag else "TN"
        elif gold_flag and pred_flag:
            binary = "TP"
        elif (not gold_flag) and pred_flag:
            binary = "FP"
        elif gold_flag and (not pred_flag):
            binary = "FN"
        else:
            binary = "TN"

        rows.append({
            "case_id": case["id"],
            "technique_id": tid,
            "gold": gold,
            "predicted": pred_cls,
            "topical_overlap": overlap,
            "exact_match": pred_cls == gold,
            "binary": binary,
            "gold_should_flag": gold_flag,
            "pred_flagged": pred_flag,
        })
    return rows


def summarize(rows: list[dict], threshold: float, labeled_path: str) -> dict:
    tp = sum(1 for r in rows if r["binary"] == "TP")
    fp = sum(1 for r in rows if r["binary"] == "FP")
    fn = sum(1 for r in rows if r["binary"] == "FN")
    tn = sum(1 for r in rows if r["binary"] == "TN")
    total = len(rows)

    exact = sum(1 for r in rows if r["exact_match"])
    by_gold = Counter(r["gold"] for r in rows)
    by_pred = Counter(r["predicted"] for r in rows)

    # Per gold-class recall of correct exact label
    exact_by_gold = {}
    for g in sorted(by_gold):
        subset = [r for r in rows if r["gold"] == g]
        hits = sum(1 for r in subset if r["exact_match"])
        exact_by_gold[g] = {
            "n": len(subset),
            "exact_correct": hits,
            "exact_accuracy": safe_div(hits, len(subset)),
        }

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "labeled_set": labeled_path,
        "overlap_threshold": threshold,
        "n_cases": len({r["case_id"] for r in rows}),
        "n_citations": total,
        "binary_detection": {
            "description": (
                "Positive = citation should be flagged "
                "(FABRICATED|REVOKED|REAL_BUT_IRRELEVANT). "
                "Predicted positive = classification != REAL_AND_PLAUSIBLE."
            ),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "accuracy": safe_div(tp + tn, total),
            "precision": safe_div(tp, tp + fp),
            "recall": safe_div(tp, tp + fn),
            "f1": safe_div(2 * tp, 2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0,
            "false_positive_rate": safe_div(fp, fp + tn),
            "false_negative_rate": safe_div(fn, fn + tp),
        },
        "exact_classification": {
            "exact_match_count": exact,
            "exact_match_rate": safe_div(exact, total),
            "per_gold_class": exact_by_gold,
        },
        "label_counts_gold": dict(by_gold),
        "label_counts_predicted": dict(by_pred),
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description="Benchmark ATT&CK grounding checker")
    parser.add_argument("--labeled", type=Path, default=DEFAULT_LABELED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Override OVERLAP_THRESHOLD for this run only (via env of verify calls)",
    )
    args = parser.parse_args()

    if not args.labeled.exists():
        raise SystemExit(f"Labeled set not found: {args.labeled}")

    # Optional threshold override by patching module constant used in verify
    import attack_grounding as ag

    threshold = args.threshold if args.threshold is not None else ag.OVERLAP_THRESHOLD
    if args.threshold is not None:
        ag.OVERLAP_THRESHOLD = args.threshold

    cases = load_cases(args.labeled)
    rows: list[dict] = []
    for case in cases:
        rows.extend(evaluate_case(case, threshold))

    report = summarize(rows, threshold, str(args.labeled))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    b = report["binary_detection"]
    e = report["exact_classification"]
    print("=== ATT&CK Grounding Benchmark ===")
    print(f"Citations evaluated : {report['n_citations']} across {report['n_cases']} cases")
    print(f"Threshold           : {threshold}")
    print()
    print("Binary (flag ungrounded citations)")
    print(f"  TP={b['tp']}  FP={b['fp']}  FN={b['fn']}  TN={b['tn']}")
    print(f"  Accuracy          : {b['accuracy']:.2%}")
    print(f"  Precision         : {b['precision']:.2%}")
    print(f"  Recall            : {b['recall']:.2%}")
    print(f"  F1                : {b['f1']:.2%}")
    print(f"  False positive rate: {b['false_positive_rate']:.2%}")
    print(f"  False negative rate: {b['false_negative_rate']:.2%}")
    print()
    print("Exact classification match rate:", f"{e['exact_match_rate']:.2%}")
    for g, stats in e["per_gold_class"].items():
        print(f"  {g}: {stats['exact_correct']}/{stats['n']} ({stats['exact_accuracy']:.2%})")
    print()
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()