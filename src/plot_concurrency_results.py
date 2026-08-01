"""
plot_concurrency_results.py — reads experiments/results/concurrency_ramp_results.json
and generates labeled charts (CPU, RAM, throughput, accuracy vs thread count),
saved as PNG files into experiments/results/plots/.

Run this AFTER concurrency_ramp_test.py has produced a results file.
Run: python plot_concurrency_results.py
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_results():
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experiments", "results")
    path = os.path.join(results_dir, "concurrency_ramp_results.json")
    with open(path) as f:
        data = json.load(f)

    plots_dir = os.path.join(results_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    return data, plots_dir


def _label_points(ax, x, y, fmt="{:.2f}"):
    """Puts the exact value above/below each point on a line plot."""
    for xi, yi in zip(x, y):
        ax.annotate(fmt.format(yi), (xi, yi), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9, fontweight="bold")


def plot_cpu(results, plots_dir):
    threads = [r["thread_count"] for r in results]
    avg_cpu = [r["resources"]["avg_cpu_pct"] for r in results]
    max_cpu = [r["resources"]["max_cpu_pct"] for r in results]
    x = range(len(threads))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(x, avg_cpu, marker="o", linewidth=2, color="#4C72B0", label="Avg CPU %")
    ax.plot(x, max_cpu, marker="s", linewidth=2, color="#DD8452", label="Max CPU %")
    _label_points(ax, x, avg_cpu)
    _label_points(ax, x, max_cpu)

    ax.set_xlabel("Concurrent Threads")
    ax.set_ylabel("CPU %")
    ax.set_title("CPU Utilization vs Concurrent Threads (Regex Filter)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(threads)
    ax.set_ylim(0, max(max_cpu) * 1.25)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(plots_dir, "cpu_vs_threads.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_ram(results, plots_dir):
    threads = [r["thread_count"] for r in results]
    avg_ram = [r["resources"]["avg_ram_pct"] for r in results]
    max_ram = [r["resources"]["max_ram_pct"] for r in results]
    x = range(len(threads))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(x, avg_ram, marker="o", linewidth=2, color="#55A868", label="Avg RAM %")
    ax.plot(x, max_ram, marker="s", linewidth=2, color="#8172B2", label="Max RAM %")
    _label_points(ax, x, avg_ram)
    _label_points(ax, x, max_ram)

    ax.set_xlabel("Concurrent Threads")
    ax.set_ylabel("RAM %")
    ax.set_title("RAM Utilization vs Concurrent Threads")
    ax.set_xticks(list(x))
    ax.set_xticklabels(threads)
    ax.set_ylim(min(avg_ram) * 0.9, max(max_ram) * 1.1)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(plots_dir, "ram_vs_threads.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_throughput(results, plots_dir):
    threads = [r["thread_count"] for r in results]
    rps = [r["requests_per_second"] for r in results]
    x = range(len(threads))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(x, rps, marker="o", linewidth=2, color="#C44E52")
    _label_points(ax, x, rps, fmt="{:.1f}")

    ax.set_xlabel("Concurrent Threads")
    ax.set_ylabel("Requests / second (log scale)")
    ax.set_title("Throughput vs Concurrent Threads")
    ax.set_xticks(list(x))
    ax.set_xticklabels(threads)
    ax.set_yscale("log")  # range spans 1 to 1000+, log scale keeps small values visible
    ax.grid(alpha=0.3, which="both")
    plt.tight_layout()
    out = os.path.join(plots_dir, "throughput_vs_threads.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def plot_accuracy(results, plots_dir):
    threads = [r["thread_count"] for r in results]
    precision = [r["accuracy"]["precision"] * 100 for r in results]
    recall = [r["accuracy"]["recall"] * 100 for r in results]
    f1 = [r["accuracy"]["f1_score"] * 100 for r in results]

    x = range(len(threads))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars1 = ax.bar([i - width for i in x], precision, width, label="Precision", color="#4C72B0")
    bars2 = ax.bar(list(x), recall, width, label="Recall", color="#55A868")
    bars3 = ax.bar([i + width for i in x], f1, width, label="F1", color="#C44E52")

    ax.bar_label(bars1, fmt="%.1f", fontsize=8, padding=2)
    ax.bar_label(bars2, fmt="%.1f", fontsize=8, padding=2)
    ax.bar_label(bars3, fmt="%.1f", fontsize=8, padding=2)

    ax.set_xlabel("Concurrent Threads")
    ax.set_ylabel("%")
    ax.set_title("Accuracy vs Concurrent Threads")
    ax.set_xticks(list(x))
    ax.set_xticklabels(threads)
    ax.set_ylim(0, 110)
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out = os.path.join(plots_dir, "accuracy_vs_threads.png")
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def main():
    data, plots_dir = load_results()
    results = data["results"]

    saved = [
        plot_cpu(results, plots_dir),
        plot_ram(results, plots_dir),
        plot_throughput(results, plots_dir),
        plot_accuracy(results, plots_dir),
    ]

    print("Saved plots:")
    for path in saved:
        print(f"  {path}")


if __name__ == "__main__":
    main()