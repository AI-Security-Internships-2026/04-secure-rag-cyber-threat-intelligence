"""
plot_guardrail_results.py — reads experiments/results/guardrail_comparison.json
and generates labeled charts + a summary table comparing the baseline keyword
matcher, LLM Guard, and NeMo Guardrails — on the CTI pilot set and the public
benchmark SEPARATELY (never blended — see guardrail_eval.py docstring for why).

All output files are prefixed "guardrail_" to stay distinguishable from the
existing regex/concurrency/cpu-benchmark plots already in experiments/results/plots/.

Run this AFTER guardrail_eval.py has produced a results file.
Run: python plot_guardrail_results.py
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


def load_results():
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experiments", "results")
    path = os.path.join(results_dir, "guardrail_comparison.json")
    with open(path) as f:
        data = json.load(f)
    plots_dir = os.path.join(results_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    return data, results_dir, plots_dir


def _available_methods(results):
    """Skips any method that failed to load (has an 'error' key instead of scores)."""
    return [m for m in METHODS if m in results and "error" not in results[m]]


def plot_precision_recall_f1(results, dataset_key, title_suffix, filename, plots_dir):
    methods = _available_methods(results)
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
    out = os.path.join(plots_dir, filename)
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_false_positive_rate(results, plots_dir):
    methods = _available_methods(results)
    x = range(len(methods))
    width = 0.35

    cti_fpr = [results[m]["cti_pilot"]["false_positive_rate"] * 100 for m in methods]
    public_fpr = [results[m]["public_benchmark"]["false_positive_rate"] * 100
                  if results[m].get("public_benchmark") else 0 for m in methods]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bars1 = ax.bar([i - width/2 for i in x], cti_fpr, width, label="CTI pilot set (domain-specific)", color="#DD8452")
    bars2 = ax.bar([i + width/2 for i in x], public_fpr, width, label="Public benchmark (general)", color="#8172B2")
    ax.bar_label(bars1, fmt="%.1f", fontsize=9, padding=2)
    ax.bar_label(bars2, fmt="%.1f", fontsize=9, padding=2)

    ax.set_xticks(list(x))
    ax.set_xticklabels([METHOD_LABELS[m] for m in methods])
    ax.set_ylabel("False Positive Rate (%)")
    ax.set_title("False Positive Rate — the number that predicts real user friction")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = os.path.join(plots_dir, "guardrail_false_positive_rate.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_latency(results, plots_dir):
    methods = _available_methods(results)
    x = range(len(methods))
    latencies = [results[m]["cti_pilot"]["avg_latency_ms"] for m in methods]
    colors = [METHOD_COLORS[m] for m in methods]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar([METHOD_LABELS[m] for m in methods], latencies, color=colors)
    ax.bar_label(bars, fmt="%.3fms", fontsize=9, fontweight="bold", padding=4)

    ax.set_ylabel("Avg latency per query (ms, log scale)")
    ax.set_title("Guardrail Detection Speed")
    ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.3, which="both")
    plt.tight_layout()
    out = os.path.join(plots_dir, "guardrail_latency_comparison.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def save_summary_table(results, dataset, results_dir):
    methods = _available_methods(results)
    lines = [
        f"# Guardrail Comparison Summary — {dataset.get('test_date', '')}",
        "",
        f"CTI pilot set: {dataset['cti_pilot_positive']} positive + {dataset['cti_pilot_negative']} negative",
        f"Public benchmark: {dataset.get('public_benchmark_examples', 0)} examples "
        f"({dataset.get('public_benchmark_source', 'n/a')})",
        "",
        "## CTI Pilot Set (domain-specific)",
        "",
        "| Method | Precision | Recall | F1 | FP Rate | Avg Latency |",
        "|---|---|---|---|---|---|",
    ]
    for m in methods:
        r = results[m]["cti_pilot"]
        lines.append(
            f"| {METHOD_LABELS[m].replace(chr(10), ' ')} | {r['precision']*100:.1f}% | "
            f"{r['recall']*100:.1f}% | {r['f1_score']*100:.1f}% | {r['false_positive_rate']*100:.1f}% | "
            f"{r['avg_latency_ms']:.4f}ms |"
        )

    lines += ["", "## Public Benchmark (general-purpose)", "",
              "| Method | Precision | Recall | F1 | FP Rate | Avg Latency |", "|---|---|---|---|---|---|"]
    for m in methods:
        pb = results[m].get("public_benchmark")
        if not pb:
            continue
        lines.append(
            f"| {METHOD_LABELS[m].replace(chr(10), ' ')} | {pb['precision']*100:.1f}% | "
            f"{pb['recall']*100:.1f}% | {pb['f1_score']*100:.1f}% | {pb['false_positive_rate']*100:.1f}% | "
            f"{pb['avg_latency_ms']:.4f}ms |"
        )

    out = os.path.join(results_dir, "guardrail_results_table.md")
    with open(out, "w") as f:
        f.write("\n".join(lines))
    return out


def _compute_three_way_accuracy(method_results: dict) -> dict:
    """
    Computes accuracy across 3 categories, using what we actually have measured:

      - malicious accuracy = recall, averaged across CTI pilot + public benchmark
        ("does it catch real attacks")
      - benign accuracy = 1 - false_positive_rate on the PUBLIC benchmark's
        generic benign text (travel, recipes, etc.)
        ("does it wrongly block ordinary, non-security-flavored questions")
      - over-defense accuracy = 1 - false_positive_rate on the CTI PILOT set's
        benign queries (e.g. "password dumping from memory", "privilege
        escalation to gain admin access") — these are legitimate questions
        that use attack-adjacent vocabulary, so this measures whether the
        detector over-reacts to security terminology even when nothing
        malicious is happening. Not a published "over-defense" benchmark
        (e.g. NotInject) — this is our own domain-specific proxy for the
        same concept, built from data we already collected.

    Returns dict with the 3 values plus their average.
    """
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


def plot_accuracy_vs_efficiency_scatter(results, plots_dir):
    """
    Scatter plot: average accuracy (across benign / malicious / over-defense
    proxy categories, see _compute_three_way_accuracy) vs time efficiency
    (avg latency per query). One point per method. Lower-right is ideal
    (fast AND accurate).
    """
    methods = _available_methods(results)

    fig, ax = plt.subplots(figsize=(9, 6.5))

    for m in methods:
        scores = _compute_three_way_accuracy(results[m])
        # use CTI pilot latency as the representative "time efficiency" figure
        latency = results[m]["cti_pilot"]["avg_latency_ms"]
        avg_acc_pct = scores["average_accuracy"] * 100

        ax.scatter(latency, avg_acc_pct, s=220, color=METHOD_COLORS[m],
                   edgecolors="black", linewidths=1.2, zorder=3)
        ax.annotate(
            METHOD_LABELS[m].replace("\n", " "),
            (latency, avg_acc_pct),
            textcoords="offset points", xytext=(0, 14),
            ha="center", fontsize=9, fontweight="bold",
        )
        # small breakdown label under each point showing the 3 components
        breakdown = (
            f"mal:{scores['malicious_accuracy']*100:.0f}% "
            f"ben:{(scores['benign_accuracy'] or 0)*100:.0f}% "
            f"od:{(scores['over_defense_accuracy'] or 0)*100:.0f}%"
        )
        ax.annotate(breakdown, (latency, avg_acc_pct),
                    textcoords="offset points", xytext=(0, -18),
                    ha="center", fontsize=7.5, color="dimgray")

    ax.set_xlabel("Avg latency per query (ms, log scale) — time efficiency")
    ax.set_ylabel("Average accuracy (%) — malicious + benign + over-defense proxy")
    ax.set_title("Injection Detection: Accuracy vs Time Efficiency\n"
                  "(mal=malicious recall, ben=benign accuracy on public set, "
                  "od=over-defense proxy on CTI benign set)")
    ax.set_xscale("log")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.3, which="both")
    plt.tight_layout()
    out = os.path.join(plots_dir, "guardrail_accuracy_vs_efficiency_scatter.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def main():
    data, results_dir, plots_dir = load_results()
    results = data["results"]
    dataset = data["dataset"]
    dataset["test_date"] = data.get("test_date", "")

    saved = [
        plot_precision_recall_f1(results, "cti_pilot", "CTI Pilot Set (domain-specific)",
                                  "guardrail_accuracy_cti_pilot.png", plots_dir),
        plot_precision_recall_f1(results, "public_benchmark", "Public Benchmark (general-purpose)",
                                  "guardrail_accuracy_public_benchmark.png", plots_dir),
        plot_false_positive_rate(results, plots_dir),
        plot_latency(results, plots_dir),
        plot_accuracy_vs_efficiency_scatter(results, plots_dir),
    ]
    table_path = save_summary_table(results, dataset, results_dir)

    print("Saved plots:")
    for path in saved:
        print(f"  {path}")
    print("Saved table:")
    print(f"  {table_path}")


if __name__ == "__main__":
    main()