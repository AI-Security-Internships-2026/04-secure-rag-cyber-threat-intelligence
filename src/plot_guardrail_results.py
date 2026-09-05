"""
plot_guardrail_results.py — read a guardrail_comparison*.json and write charts.

Modes:
  legacy — experiments/results/guardrail_comparison.json
           → experiments/results/plots/  (original paper figures; do not overwrite casually)
  cti100 — experiments/results/eval_100/guardrail/guardrail_comparison_cti_100.json
           → experiments/results/eval_100/plots/  (n=100 run; safe for new work)

CTI and public benchmarks are plotted SEPARATELY (never blended).

Usage (from repo root):
    python src/plot_guardrail_results.py
    python src/plot_guardrail_results.py --mode cti100
    python src/plot_guardrail_results.py --mode legacy
    python src/plot_guardrail_results.py --input path/to.json --plots-dir path/to/plots
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_REPO_ROOT = Path(__file__).resolve().parents[1]

# =============================================================================
# CONFIG (CLI can override)
# =============================================================================
PLOT_MODE = "cti100"  # "legacy" | "cti100"

INPUT_PATH_BY_MODE = {
    "legacy": _REPO_ROOT / "experiments" / "results" / "guardrail_comparison.json",
    "cti100": (
        _REPO_ROOT
        / "experiments"
        / "results"
        / "eval_100"
        / "guardrail"
        / "guardrail_comparison_cti_100.json"
    ),
}

PLOTS_DIR_BY_MODE = {
    "legacy": _REPO_ROOT / "experiments" / "results" / "plots",
    "cti100": _REPO_ROOT / "experiments" / "results" / "eval_100" / "plots",
}

# Diagnostic markdown written next to the results JSON's parent folder
TABLE_NAME_BY_MODE = {
    "legacy": "guardrail_comparison_diagnostic_analysis.md",
    "cti100": "guardrail_cti100_diagnostic_analysis.md",
}

# Filename prefix so artifacts are easy to tell apart
PREFIX_BY_MODE = {
    "legacy": "guardrail_",
    "cti100": "guardrail_cti100_",
}
# =============================================================================

METHOD_LABELS = {
    "current_repo_baseline": "Baseline\n(keyword)",
    "llm_guard": "LLM Guard\n(DeBERTa)",
    "nemoguardrails": "NeMo Guardrails\n(GPT2 heuristic)",
}
METHOD_COLORS = {
    "current_repo_baseline": "#4C72B0",
    "llm_guard": "#55A868",
    "nemoguardrails": "#C44E52",
}
METHODS = ["current_repo_baseline", "llm_guard", "nemoguardrails"]


def load_results(input_path: Path, plots_dir: Path):
    if not input_path.exists():
        raise SystemExit(f"Results file not found: {input_path}")
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)
    plots_dir.mkdir(parents=True, exist_ok=True)
    return data, input_path.parent, plots_dir


def _available_methods(results):
    """Skip methods that failed to load (error key instead of scores)."""
    return [m for m in METHODS if m in results and "error" not in results[m]]


def _has_public(results) -> bool:
    for m in _available_methods(results):
        if results[m].get("public_benchmark"):
            return True
    return False


def plot_precision_recall_f1(results, dataset_key, title_suffix, filename, plots_dir):
    methods = _available_methods(results)
    # Skip methods missing this dataset block
    methods = [m for m in methods if results[m].get(dataset_key)]
    if not methods:
        return None

    metrics = ["precision", "recall", "f1_score"]
    metric_labels = ["Precision", "Recall", "F1"]

    x = range(len(methods))
    width = 0.25
    fig, ax = plt.subplots(figsize=(9, 5.5))

    for i, (metric, mlabel) in enumerate(zip(metrics, metric_labels)):
        values = [results[m][dataset_key][metric] * 100 for m in methods]
        offset = (i - 1) * width
        bars = ax.bar([xi + offset for xi in x], values, width, label=mlabel)
        ax.bar_label(bars, fmt="%.1f", fontsize=8, padding=2)

    ax.set_xticks(list(x))
    ax.set_xticklabels([METHOD_LABELS[m] for m in methods])
    ax.set_ylabel("%")
    ax.set_title(f"Guardrail Accuracy — {title_suffix}")
    ax.set_ylim(0, 110)
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = os.path.join(str(plots_dir), filename)
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_false_positive_rate(results, plots_dir, filename):
    methods = _available_methods(results)
    x = range(len(methods))
    width = 0.35

    cti_fpr = [
        results[m]["cti_pilot"]["false_positive_rate"] * 100
        if results[m].get("cti_pilot")
        else 0
        for m in methods
    ]
    public_fpr = [
        results[m]["public_benchmark"]["false_positive_rate"] * 100
        if results[m].get("public_benchmark")
        else 0
        for m in methods
    ]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars1 = ax.bar(
        [i - width / 2 for i in x],
        cti_fpr,
        width,
        label="CTI set (domain-specific)",
        color="#DD8452",
    )
    bars2 = ax.bar(
        [i + width / 2 for i in x],
        public_fpr,
        width,
        label="Public benchmark (general)",
        color="#8172B2",
    )
    ax.bar_label(bars1, fmt="%.1f", fontsize=9, padding=2)
    ax.bar_label(bars2, fmt="%.1f", fontsize=9, padding=2)

    ax.set_xticks(list(x))
    ax.set_xticklabels([METHOD_LABELS[m] for m in methods])
    ax.set_ylabel("False Positive Rate (%)")
    ax.set_title("False Positive Rate — predicts real user friction")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = os.path.join(str(plots_dir), filename)
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_latency(results, plots_dir, filename):
    methods = _available_methods(results)
    methods = [m for m in methods if results[m].get("cti_pilot")]
    latencies = [results[m]["cti_pilot"]["avg_latency_ms"] for m in methods]
    colors = [METHOD_COLORS[m] for m in methods]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar([METHOD_LABELS[m] for m in methods], latencies, color=colors)
    ax.bar_label(bars, fmt="%.3fms", fontsize=9, fontweight="bold", padding=4)

    ax.set_ylabel("Avg latency per query (ms, log scale)")
    ax.set_title("Guardrail Detection Speed (CTI set)")
    ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.3, which="both")
    plt.tight_layout()
    out = os.path.join(str(plots_dir), filename)
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def save_summary_table(results, dataset, out_dir: Path, filename: str):
    methods = _available_methods(results)
    cti_pos = dataset.get("cti_positive", dataset.get("cti_pilot_positive", "?"))
    cti_neg = dataset.get("cti_negative", dataset.get("cti_pilot_negative", "?"))

    lines = [
        f"# Guardrail Comparison Summary — {dataset.get('test_date', '')}",
        "",
        f"CTI set: {cti_pos} positive + {cti_neg} negative "
        f"(mode={dataset.get('cti_set_mode', 'n/a')})",
        f"Public benchmark: {dataset.get('public_benchmark_examples', 0)} examples "
        f"({dataset.get('public_benchmark_source', 'n/a')})",
        "",
        "## CTI set (domain-specific)",
        "",
        "| Method | Precision | Recall | F1 | FP Rate | Avg Latency |",
        "|---|---|---|---|---|---|",
    ]
    for m in methods:
        r = results[m].get("cti_pilot")
        if not r:
            continue
        lines.append(
            f"| {METHOD_LABELS[m].replace(chr(10), ' ')} | {r['precision']*100:.1f}% | "
            f"{r['recall']*100:.1f}% | {r['f1_score']*100:.1f}% | "
            f"{r['false_positive_rate']*100:.1f}% | {r['avg_latency_ms']:.4f}ms |"
        )

    lines += [
        "",
        "## Public Benchmark (general-purpose)",
        "",
        "| Method | Precision | Recall | F1 | FP Rate | Avg Latency |",
        "|---|---|---|---|---|---|",
    ]
    for m in methods:
        pb = results[m].get("public_benchmark")
        if not pb:
            continue
        lines.append(
            f"| {METHOD_LABELS[m].replace(chr(10), ' ')} | {pb['precision']*100:.1f}% | "
            f"{pb['recall']*100:.1f}% | {pb['f1_score']*100:.1f}% | "
            f"{pb['false_positive_rate']*100:.1f}% | {pb['avg_latency_ms']:.4f}ms |"
        )

    out = out_dir / filename
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)


def _compute_three_way_accuracy(method_results: dict) -> dict:
    cti = method_results.get("cti_pilot") or {}
    public = method_results.get("public_benchmark") or {}

    recalls = [d["recall"] for d in (cti, public) if d]
    malicious_acc = sum(recalls) / len(recalls) if recalls else 0.0

    benign_acc = (1 - public["false_positive_rate"]) if public else None
    over_defense_acc = (1 - cti["false_positive_rate"]) if cti else None

    parts = [v for v in (malicious_acc, benign_acc, over_defense_acc) if v is not None]
    avg_acc = sum(parts) / len(parts) if parts else 0.0

    return {
        "malicious_accuracy": malicious_acc,
        "benign_accuracy": benign_acc,
        "over_defense_accuracy": over_defense_acc,
        "average_accuracy": avg_acc,
    }


def plot_accuracy_vs_efficiency_scatter(results, plots_dir, filename):
    methods = _available_methods(results)
    methods = [m for m in methods if results[m].get("cti_pilot")]

    fig, ax = plt.subplots(figsize=(9, 6.5))

    for m in methods:
        scores = _compute_three_way_accuracy(results[m])
        latency = results[m]["cti_pilot"]["avg_latency_ms"]
        avg_acc_pct = scores["average_accuracy"] * 100

        ax.scatter(
            latency,
            avg_acc_pct,
            s=220,
            color=METHOD_COLORS[m],
            edgecolors="black",
            linewidths=1.2,
            zorder=3,
        )
        ax.annotate(
            METHOD_LABELS[m].replace("\n", " "),
            (latency, avg_acc_pct),
            textcoords="offset points",
            xytext=(0, 14),
            ha="center",
            fontsize=9,
            fontweight="bold",
        )
        breakdown = (
            f"mal:{scores['malicious_accuracy']*100:.0f}% "
            f"ben:{(scores['benign_accuracy'] or 0)*100:.0f}% "
            f"od:{(scores['over_defense_accuracy'] or 0)*100:.0f}%"
        )
        ax.annotate(
            breakdown,
            (latency, avg_acc_pct),
            textcoords="offset points",
            xytext=(0, -18),
            ha="center",
            fontsize=7.5,
            color="dimgray",
        )

    ax.set_xlabel("Avg latency per query (ms, log scale) — time efficiency")
    ax.set_ylabel("Average accuracy (%) — malicious + benign + over-defense proxy")
    ax.set_title(
        "Injection Detection: Accuracy vs Time Efficiency\n"
        "(mal=malicious recall, ben=benign accuracy on public set, "
        "od=over-defense proxy on CTI benign set)"
    )
    ax.set_xscale("log")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.3, which="both")
    plt.tight_layout()
    out = os.path.join(str(plots_dir), filename)
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def parse_args():
    p = argparse.ArgumentParser(description="Plot guardrail comparison results")
    p.add_argument("--mode", choices=["legacy", "cti100"], default=None)
    p.add_argument("--input", type=Path, default=None, help="Results JSON path")
    p.add_argument("--plots-dir", type=Path, default=None, help="Directory for PNG plots")
    return p.parse_args()


def main():
    args = parse_args()
    mode = args.mode or PLOT_MODE
    input_path = Path(args.input) if args.input else INPUT_PATH_BY_MODE[mode]
    plots_dir = Path(args.plots_dir) if args.plots_dir else PLOTS_DIR_BY_MODE[mode]
    prefix = PREFIX_BY_MODE[mode]
    table_name = TABLE_NAME_BY_MODE[mode]

    data, results_dir, plots_dir = load_results(input_path, plots_dir)
    results = data["results"]
    dataset = dict(data.get("dataset") or {})
    dataset["test_date"] = data.get("test_date", "")
    dataset["cti_set_mode"] = data.get("cti_set_mode", mode)

    saved = []

    p = plot_precision_recall_f1(
        results,
        "cti_pilot",
        f"CTI set ({mode})",
        f"{prefix}accuracy_cti.png",
        plots_dir,
    )
    if p:
        saved.append(p)

    if _has_public(results):
        p = plot_precision_recall_f1(
            results,
            "public_benchmark",
            "Public Benchmark (general-purpose)",
            f"{prefix}accuracy_public_benchmark.png",
            plots_dir,
        )
        if p:
            saved.append(p)
        saved.append(
            plot_false_positive_rate(
                results, plots_dir, f"{prefix}false_positive_rate.png"
            )
        )

    saved.append(plot_latency(results, plots_dir, f"{prefix}latency_comparison.png"))
    saved.append(
        plot_accuracy_vs_efficiency_scatter(
            results, plots_dir, f"{prefix}accuracy_vs_efficiency_scatter.png"
        )
    )

    table_path = save_summary_table(results, dataset, Path(results_dir), table_name)

    print(f"Mode  : {mode}")
    print(f"Input : {input_path}")
    print(f"Plots : {plots_dir}")
    print("Saved plots:")
    for path in saved:
        if path:
            print(f"  {path}")
    print("Saved table:")
    print(f"  {table_path}")


if __name__ == "__main__":
    main()