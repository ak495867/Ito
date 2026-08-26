from __future__ import annotations

import argparse
import json
import random
import statistics
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Sample:
    branch_id: str
    message_id: int
    send_ns: int
    receive_ns: int
    acknowledge_ns: int
    latency_ns: int
    jitter_ns: int
    venue_id: str = "aggregate"


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def branch_samples(branch_id: str, messages: int, interval_ns: int, base_latency_ns: int, jitter_ns: int, rng: random.Random, venue_id: str = "aggregate", start_offset_ns: int = 0) -> list[Sample]:
    samples: list[Sample] = []
    for message_id in range(messages):
        send_ns = start_offset_ns + message_id * interval_ns
        signed_jitter = int(rng.gauss(0, jitter_ns))
        tail = jitter_ns * 5 if jitter_ns and rng.random() < 0.001 else 0
        network = max(100, base_latency_ns + signed_jitter + tail)
        receive_ns = send_ns + network
        processing = 1_200 + int(rng.uniform(0, 500))
        acknowledge_ns = receive_ns + processing + network
        samples.append(Sample(branch_id, message_id, send_ns, receive_ns, acknowledge_ns, acknowledge_ns - send_ns, network - base_latency_ns, venue_id))
    return samples


def run_exchange(binary: Path | None) -> str:
    if binary is None or not binary.exists():
        return "not_run"
    result = subprocess.run([str(binary)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"exchange_simulator_failed:{result.returncode}")
    return result.stdout.strip()


def stats(values: list[int]) -> dict[str, int | float]:
    return {"messages": len(values), "p50_ns": percentile(values, 0.50), "p95_ns": percentile(values, 0.95), "p99_ns": percentile(values, 0.99), "max_ns": max(values, default=0), "mean_ns": round(statistics.fmean(values), 2) if values else 0.0}


def summarize(samples: list[Sample], wall_seconds: float, exchange_status: str) -> dict[str, object]:
    latencies = [sample.latency_ns for sample in samples]
    duration_ns = max((sample.acknowledge_ns for sample in samples), default=0) - min((sample.send_ns for sample in samples), default=0)
    branch_stats = {branch_id: stats([sample.latency_ns for sample in samples if sample.branch_id == branch_id]) for branch_id in sorted({sample.branch_id for sample in samples})}
    venue_stats = {venue_id: stats([sample.latency_ns for sample in samples if sample.venue_id == venue_id]) for venue_id in sorted({sample.venue_id for sample in samples})}
    return {"messages": len(samples), "branches": len(branch_stats), "venues": len(venue_stats), "virtual_duration_ns": duration_ns, "throughput_messages_per_second": round(len(samples) * 1_000_000_000 / duration_ns, 2) if duration_ns else 0.0, "wall_seconds": round(wall_seconds, 6), "aggregate": stats(latencies), "branches_detail": branch_stats, "venues_detail": venue_stats, "exchange_simulator": exchange_status}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--messages-per-branch", type=int, default=10000)
    parser.add_argument("--interval-ns", type=int, default=1000)
    parser.add_argument("--base-latency-ns", type=int, default=25000)
    parser.add_argument("--jitter-ns", type=int, default=5000)
    parser.add_argument("--venue-adapters", default="exchange-a-sim,exchange-b-sim,broker-a-sim,broker-b-sim")
    parser.add_argument("--seed", type=int, default=20260825)
    parser.add_argument("--output", type=Path, default=Path("build/benchmarks/multibranch_benchmark.json"))
    parser.add_argument("--exchange-binary", type=Path, default=Path("build/cpp/ito_exchange_simulator"))
    args = parser.parse_args()
    venues = [value.strip() for value in args.venue_adapters.split(",") if value.strip()]
    if args.branches <= 0 or args.messages_per_branch <= 0 or args.interval_ns <= 0 or args.base_latency_ns <= 0 or args.jitter_ns < 0 or not venues:
        raise SystemExit("benchmark_parameters_invalid")
    start = time.perf_counter()
    rng = random.Random(args.seed)
    samples: list[Sample] = []
    block = args.messages_per_branch * args.interval_ns
    for branch_number in range(args.branches):
        for venue_number, venue_id in enumerate(venues):
            samples.extend(branch_samples(f"branch-{branch_number + 1:02d}", args.messages_per_branch, args.interval_ns, args.base_latency_ns + branch_number * 250 + venue_number * 1000, args.jitter_ns + venue_number * 200, rng, venue_id, (branch_number * len(venues) + venue_number) * block))
    result = summarize(samples, time.perf_counter() - start, run_exchange(args.exchange_binary))
    result["parameters"] = {"branches": args.branches, "messages_per_branch": args.messages_per_branch, "interval_ns": args.interval_ns, "base_latency_ns": args.base_latency_ns, "jitter_ns": args.jitter_ns, "venue_adapters": venues, "seed": args.seed}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
