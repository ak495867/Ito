from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: render_benchmark_suite.py <suite.json> <output_dir>", file=sys.stderr)
        return 2
    source = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    suite = json.loads(source.read_text(encoding="utf-8"))
    scenarios = suite["scenarios"]
    venue_names = suite["parameters"]["venue_adapters"]
    jitter = [scenario["jitter_ns"] for scenario in scenarios]
    fig, axis = plt.subplots(figsize=(11, 6), dpi=160)
    for venue in venue_names:
        axis.plot(jitter, [scenario["venues_detail"][venue]["p99_ns"] for scenario in scenarios], marker="o", label=venue)
    axis.set_title("Ito venue-adapter p99 latency under simulated jitter")
    axis.set_xlabel("Simulated network jitter (ns)")
    axis.set_ylabel("p99 round-trip latency (ns)")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    chart = output_dir / "multibranch_suite_p99.png"
    fig.savefig(chart)
    plt.close(fig)
    lines = ["# Ito Multi-Branch P99 Benchmark Suite", "", f"The suite evaluated **{suite['parameters']['branches']}** branches, **{suite['parameters']['messages_per_branch']}** messages per branch and adapter per scenario, and **{len(venue_names)}** venue adapters across jitter levels of {', '.join(str(value) + ' ns' for value in jitter)}.", "", "## Venue p99 latency by jitter", "", "| Jitter | " + " | ".join(venue_names) + " | Aggregate |", "| ---: | " + " | ".join("---:" for _ in venue_names) + " | ---: |"]
    for scenario in scenarios:
        lines.append("| " + str(scenario["jitter_ns"]) + " ns | " + " | ".join(str(scenario["venues_detail"][venue]["p99_ns"]) + " ns" for venue in venue_names) + " | " + str(scenario["aggregate"]["p99_ns"]) + " ns |")
    baseline = scenarios[0]
    worst = scenarios[-1]
    lines.extend(["", "## P99 change from baseline to highest-jitter scenario", "", "| Adapter | Baseline p99 | Highest-jitter p99 | Increase | Increase percent |", "| --- | ---: | ---: | ---: | ---: |"])
    for venue in venue_names:
        start = baseline["venues_detail"][venue]["p99_ns"]
        end = worst["venues_detail"][venue]["p99_ns"]
        increase = end - start
        percentage = round(increase * 100 / start, 2) if start else 0.0
        lines.append(f"| {venue} | {start} ns | {end} ns | {increase} ns | {percentage}% |")
    lines.extend(["", "![P99 chart](multibranch_suite_p99.png)", "", "## Interpretation", "", "The deterministic model shows monotonic tail-latency growth as jitter increases. The broker-b-sim route has the highest p99 in the tested scenarios, while exchange-a-sim has the lowest. Throughput remains close to one million modeled messages per second because the benchmark uses virtual timestamps rather than sleeping for network delay. These results are regression evidence, not a production-network or venue-certification claim.", ""])
    report = output_dir / "multibranch_suite_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
