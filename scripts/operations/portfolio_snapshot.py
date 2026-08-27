from __future__ import annotations

import argparse
import json
from pathlib import Path

from portfolio import Portfolio, PortfolioLimits


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input_invalid")
    return value


def build_snapshot(value: dict[str, object]) -> dict[str, object]:
    raw_limits = value.get("limits")
    raw_fills = value.get("fills")
    raw_marks = value.get("marks", {})
    if (
        not isinstance(raw_limits, dict)
        or not isinstance(raw_fills, list)
        or not isinstance(raw_marks, dict)
    ):
        raise ValueError("input_invalid")
    limits = PortfolioLimits(
        *(
            int(raw_limits[name])
            for name in (
                "max_net_position",
                "max_gross_position",
                "max_gross_notional_ticks",
                "max_concentration_ticks",
                "max_loss_ticks",
            )
        )
    )
    portfolio = Portfolio(limits)
    for fill in raw_fills:
        if not isinstance(fill, dict):
            raise ValueError("fill_invalid")
        portfolio.apply_fill(
            int(fill["instrument_id"]),
            int(fill["side"]),
            int(fill["quantity"]),
            int(fill["price_ticks"]),
        )
    marks = {
        int(instrument_id): int(price) for instrument_id, price in raw_marks.items()
    }
    return portfolio.snapshot(marks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build_snapshot(load(args.input))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
