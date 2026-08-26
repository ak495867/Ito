from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def grouped_bars(axis, labels, detail, title):
    p50 = [detail[label]["p50_ns"] for label in labels]
    p95 = [detail[label]["p95_ns"] for label in labels]
    p99 = [detail[label]["p99_ns"] for label in labels]
    positions = list(range(len(labels)))
    width = 0.24
    axis.bar([position - width for position in positions], p50, width=width, label="p50")
    axis.bar(positions, p95, width=width, label="p95")
    axis.bar([position + width for position in positions], p99, width=width, label="p99")
    axis.set_title(title)
    axis.set_ylabel("Latency (ns)")
    axis.set_xticks(positions, labels, rotation=25, ha="right")
    axis.grid(axis="y", alpha=0.25)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: render_benchmark_report.py <benchmark.json> <output_dir>", file=sys.stderr)
        return 2
    source = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(source.read_text(encoding="utf-8"))
    branches = data["branches_detail"]
    venues = data.get("venues_detail", {})
    fig, axes = plt.subplots(2 if venues else 1, 1, figsize=(12, 9 if venues else 5), dpi=160)
    axes = [axes] if not isinstance(axes, list) and not hasattr(axes, "__len__") else list(axes)
    grouped_bars(axes[0], list(branches), branches, "Ito branch latency under simulated jitter")
    if venues:
        grouped_bars(axes[1], list(venues), venues, "Ito venue-adapter latency under simulated jitter")
        axes[1].set_xlabel("Venue adapter")
    axes[0].legend()
    fig.tight_layout()
    chart = output_dir / "multibranch_latency.png"
    fig.savefig(chart)
    plt.close(fig)
    lines = ["# Ito Multi-Branch Multi-Venue Benchmark Report", "", f"The benchmark processed **{data['messages']}** messages across **{data['branches']}** branches and **{data['venues']}** venue adapters under deterministic simulated network jitter. The exchange simulator status was `{data['exchange_simulator']}`.", "", "## Aggregate results", "", "| Metric | Value |", "| --- | ---: |", f"| Messages | {data['messages']} |", f"| Throughput | {data['throughput_messages_per_second']} messages/second |", f"| p50 | {data['aggregate']['p50_ns']} ns |", f"| p95 | {data['aggregate']['p95_ns']} ns |", f"| p99 | {data['aggregate']['p99_ns']} ns |", f"| Maximum | {data['aggregate']['max_ns']} ns |", "", "## Venue-adapter p99 profile", "", "| Adapter | Messages | Mean | p50 | p95 | p99 | Maximum |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for label, value in venues.items():
        lines.append(f"| {label} | {value['messages']} | {value['mean_ns']} ns | {value['p50_ns']} ns | {value['p95_ns']} ns | {value['p99_ns']} ns | {value['max_ns']} ns |")
    lines.extend(["", "## Branch profile", "", "| Branch | Messages | Mean | p50 | p95 | p99 | Maximum |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for label, value in branches.items():
        lines.append(f"| {label} | {value['messages']} | {value['mean_ns']} ns | {value['p50_ns']} ns | {value['p95_ns']} ns | {value['p99_ns']} ns | {value['max_ns']} ns |")
    lines.extend(["", "![Latency chart](multibranch_latency.png)", "", "## Interpretation", "", "The benchmark is a deterministic software model of transport jitter and processing delay. It is useful for regression and capacity comparisons, but it is not a substitute for hardware timestamping, venue certification, production network measurements, or hardware-in-the-loop testing.", ""])
    report = output_dir / "multibranch_benchmark_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
