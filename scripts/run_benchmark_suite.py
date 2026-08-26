from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from benchmark_multibranch import branch_samples, run_exchange, summarize


def run_suite(branches: int, messages_per_branch: int, interval_ns: int, base_latency_ns: int, jitter_levels: list[int], venues: list[str], seed: int, exchange_binary: Path | None) -> dict[str, object]:
    scenarios: list[dict[str, object]] = []
    block = messages_per_branch * interval_ns
    for level_number, jitter_ns in enumerate(jitter_levels):
        samples = []
        rng = random.Random(seed + level_number)
        for branch_number in range(branches):
            for venue_number, venue_id in enumerate(venues):
                samples.extend(branch_samples(f"branch-{branch_number + 1:02d}", messages_per_branch, interval_ns, base_latency_ns + branch_number * 250 + venue_number * 1000, jitter_ns + venue_number * 200, rng, venue_id, (branch_number * len(venues) + venue_number) * block))
        result = summarize(samples, 0.0, run_exchange(exchange_binary))
        result["jitter_ns"] = jitter_ns
        scenarios.append(result)
    return {"parameters": {"branches": branches, "messages_per_branch": messages_per_branch, "interval_ns": interval_ns, "base_latency_ns": base_latency_ns, "jitter_levels_ns": jitter_levels, "venue_adapters": venues, "seed": seed}, "scenarios": scenarios, "generated_at_ns": time.time_ns()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branches", type=int, default=4)
    parser.add_argument("--messages-per-branch", type=int, default=5000)
    parser.add_argument("--interval-ns", type=int, default=1000)
    parser.add_argument("--base-latency-ns", type=int, default=25000)
    parser.add_argument("--jitter-levels-ns", default="0,1000,5000,10000")
    parser.add_argument("--venue-adapters", default="exchange-a-sim,exchange-b-sim,broker-a-sim,broker-b-sim")
    parser.add_argument("--seed", type=int, default=20260825)
    parser.add_argument("--exchange-binary", type=Path, default=Path("build/cpp/ito_exchange_simulator"))
    parser.add_argument("--output", type=Path, default=Path("docs/benchmarks/multibranch_suite.json"))
    args = parser.parse_args()
    jitter_levels = [int(value) for value in args.jitter_levels_ns.split(",") if value.strip()]
    venues = [value.strip() for value in args.venue_adapters.split(",") if value.strip()]
    if args.branches <= 0 or args.messages_per_branch <= 0 or args.interval_ns <= 0 or args.base_latency_ns <= 0 or not jitter_levels or not venues:
        raise SystemExit("benchmark_suite_parameters_invalid")
    result = run_suite(args.branches, args.messages_per_branch, args.interval_ns, args.base_latency_ns, jitter_levels, venues, args.seed, args.exchange_binary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
