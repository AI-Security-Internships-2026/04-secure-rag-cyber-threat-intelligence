"""
plot_cpu_benchmark_results.py — reads experiments/results/cpu_only_benchmark.json
and generates labeled charts comparing Presidio, regex v1, and regex v3.
Saved as PNG files into experiments/results/plots/.

Run this AFTER cpu_benchmark.py has produced a results file.
Run: python plot_cpu_benchmark_results.py
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

METHOD_LABELS = {"presidio": "Presidio", "regex": "Regex v1", "regex_v3": "Regex v3"}
METHOD_COLORS = {"presidio": "#C44E52", "regex": "#4C72B0", "regex_v3": "#55A868"}
METHODS = ["presidio", "regex", "regex_v3"]


def load_results():
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experiments", "results")
    path = os.path.join(results_dir, "cpu_only_benchmark.json")
    with open(path) as f:
        data = json.load(f)
    plots_dir = os.path.join(results_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    return data, plots_dir


def plot_throughput(data, plots_dir):
    summary = data["summary"]
    means = [summary[m]["requests_per_second"] for m in METHODS]
    stds = [summary[m]["requests_per_second_std"] for m in METHODS]
    labels = [METHOD_LABELS[m] for m in METHODS]
    colors = [METHOD_COLORS[m] for m in METHODS]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(labels, means, yerr=stds, capsize=8, color=colors)

    for bar, mean, std in zip(bars, means, stds):
        ax.annotate(f"{mean:,.1f}\n± {std:,.1f}",
                    (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9, fontweight="bold")

    ax.set_ylabel("Requests / second (log scale)")
    ax.set_title("Throughput by Privacy Filter Method\n(mean ± std dev across 10 rounds, retrieval excluded)")
    ax.set_yscale("log")
    ax.grid(axis="y", alpha=0.3, which="both")
    plt.tight_layout()
    out = os.path.join(plots_dir, "benchmark_throughput.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_latency(data, plots_dir):
    summary = data["summary"]
    metrics = ["median_latency_ms", "p95_latency_ms", "p99_latency_ms"]
    metric_labels = ["Median", "P95", "P99"]

    x = range(len(METHODS))
    width = 0.25
    fig, ax = plt.subplots(figsize=(9, 5.5))

    for i, (metric, mlabel) in enumerate(zip(metrics, metric_labels)):
        values = [summary[m][metric] for m in METHODS]
        offset = (i - 1) * width
        bars = ax.bar([xi + offset for xi in x], values, width, label=mlabel)
        ax.bar_label(bars, fmt="%.3f", fontsize=7, padding=2)

    ax.set_xticks(list(x))
    ax.set_xticklabels([METHOD_LABELS[m] for m in METHODS])
    ax.set_ylabel("Latency (ms, log scale)")
    ax.set_title("Latency by Privacy Filter Method (retrieval excluded)")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(axis="y", alpha=0.3, which="both")
    plt.tight_layout()
    out = os.path.join(plots_dir, "benchmark_latency.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_per_round_consistency(data, plots_dir):
    per_round = data["per_round_results"]
    rounds = range(1, len(per_round["regex"]) + 1)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for m in METHODS:
        # each entry in per_round[m] is a full dict of that round's stats —
        # pull out just requests_per_second for this chart
        rps_values = [round_data["requests_per_second"] for round_data in per_round[m]]
        ax.plot(rounds, rps_values, marker="o", linewidth=2,
                label=METHOD_LABELS[m], color=METHOD_COLORS[m])

    ax.set_xlabel("Round")
    ax.set_ylabel("Requests / second (log scale)")
    ax.set_title("Throughput Consistency Across 10 Rounds\n(no overlap = reliable ranking, not noise-driven)")
    ax.set_xticks(list(rounds))
    ax.set_yscale("log")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    plt.tight_layout()
    out = os.path.join(plots_dir, "benchmark_per_round_consistency.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_speedups(data, plots_dir):
    speedups = data["speedups"]
    labels = ["Regex v1\nvs Presidio", "Regex v3\nvs Presidio", "Regex v3\nvs Regex v1"]
    values = [speedups["regex_v1_vs_presidio"], speedups["regex_v3_vs_presidio"], speedups["regex_v3_vs_regex_v1"]]
    colors = ["#4C72B0", "#55A868", "#DD8452"]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, fmt="%.2fx", fontsize=10, fontweight="bold", padding=4)

    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_ylabel("Speed ratio (x times faster)")
    ax.set_title("Speed Ratios Between Methods")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = os.path.join(plots_dir, "benchmark_speedups.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out

def plot_summary_table(data, plots_dir):
    """
    Creates a table containing all summary statistics
    for Presidio, Regex v1 and Regex v3.
    """

    summary = data["summary"]

    metrics = [
        ("Requests/sec", "requests_per_second"),
        ("Requests/sec Std", "requests_per_second_std"),
        ("Average Latency (ms)", "avg_latency_ms"),
        ("Average Latency Std", "avg_latency_ms_std"),
        ("Median Latency (ms)", "median_latency_ms"),
        ("Median Latency Std", "median_latency_ms_std"),
        ("Minimum Latency (ms)", "min_latency_ms"),
        ("Minimum Latency Std", "min_latency_ms_std"),
        ("Maximum Latency (ms)", "max_latency_ms"),
        ("Maximum Latency Std", "max_latency_ms_std"),
        ("P95 Latency (ms)", "p95_latency_ms"),
        ("P95 Latency Std", "p95_latency_ms_std"),
        ("P99 Latency (ms)", "p99_latency_ms"),
        ("P99 Latency Std", "p99_latency_ms_std"),
    ]

    table_data = []

    for metric_name, key in metrics:
        table_data.append([
            metric_name,
            f"{summary['presidio'][key]:.4f}",
            f"{summary['regex'][key]:.4f}",
            f"{summary['regex_v3'][key]:.4f}",
        ])

    fig, ax = plt.subplots(figsize=(13, 8))
    ax.axis("off")

    table = ax.table(
        cellText=table_data,
        colLabels=["Metric", "Presidio", "Regex v1", "Regex v3"],
        cellLoc="center",
        loc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)

    # Header styling
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor("#40466e")
        elif col == 0:
            cell.set_text_props(weight="bold")

    plt.title("CPU Benchmark Summary Statistics", fontsize=14, pad=20)

    out = os.path.join(
        plots_dir,
        "benchmark_summary_table.png"
    )

    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()

    return out

def plot_configuration_table(data, plots_dir):
    """
    Creates a table containing benchmark configuration,
    hardware information and speedups.
    """

    cfg = data["benchmark_configuration"]
    hw = data["hardware"]
    speed = data["speedups"]

    rows = [
        ["Rounds", cfg["rounds"]],
        ["Requests per Round", cfg["requests_per_round"]],
        ["Warmup Requests", cfg["warmup_requests"]],
        ["Total Requests per Method", cfg["total_requests_per_method"]],
        ["Documents Prefetched", cfg["documents_prefetched"]],
        ["CPU (Physical)", hw["cpu_cores_physical"]],
        ["CPU (Logical)", hw["cpu_cores_logical"]],
        ["RAM (GB)", hw["ram_gb"]],
        ["Operating System", hw["os"]],
        ["Processor", hw["processor"]],
        ["Python Version", hw["python_version"]],
        ["GPU", hw["gpu"]],
        ["Regex v1 vs Presidio", f'{speed["regex_v1_vs_presidio"]:.3f}x'],
        ["Regex v3 vs Presidio", f'{speed["regex_v3_vs_presidio"]:.3f}x'],
        ["Regex v3 vs Regex v1", f'{speed["regex_v3_vs_regex_v1"]:.3f}x'],
    ]

    fig, ax = plt.subplots(figsize=(11,8))
    ax.axis("off")

    table = ax.table(
        cellText=rows,
        colLabels=["Parameter", "Value"],
        cellLoc="left",
        loc="center"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#40466e")
            cell.set_text_props(color="white", weight="bold")

    plt.title("Benchmark Configuration and Hardware", fontsize=14)

    out = os.path.join(
        plots_dir,
        "benchmark_configuration_table.png"
    )

    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()

    return out




def main():
    data, plots_dir = load_results()
    saved = [
        plot_throughput(data, plots_dir),
        plot_latency(data, plots_dir),
        plot_per_round_consistency(data, plots_dir),
        plot_speedups(data, plots_dir),
        plot_summary_table(data, plots_dir),
        plot_configuration_table(data, plots_dir),
    ]
    print("Saved plots:")
    for path in saved:
        print(f"  {path}")


if __name__ == "__main__":
    main()