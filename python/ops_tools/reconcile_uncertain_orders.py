"""Automated Order Uncertainty Reconciliation Tool based on order-uncertainty.md runbook."""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any


def reconcile_orders(
    journal_path: Path, venue_id: str, auto_resolve: bool = False
) -> Dict[str, Any]:
    if not journal_path.exists():
        return {
            "status": "error",
            "reason": f"journal_file_not_found: {journal_path}",
            "uncertain_orders": [],
        }

    uncertain_orders: List[Dict[str, Any]] = []
    resolved_orders: List[Dict[str, Any]] = []

    with open(journal_path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("event_type") == 3:  # OrderSent
                    correlation_id = record.get("correlation_id", 0)
                    uncertain_orders.append(
                        {
                            "line": line_number,
                            "correlation_id": correlation_id,
                            "event_id": record.get("event_id"),
                            "status": "uncertain",
                        }
                    )
                elif record.get("event_type") == 4:  # Acknowledgment
                    correlation_id = record.get("correlation_id", 0)
                    uncertain_orders = [
                        o for o in uncertain_orders if o["correlation_id"] != correlation_id
                    ]
                    resolved_orders.append({"correlation_id": correlation_id, "status": "acknowledged"})
            except Exception:
                continue

    if auto_resolve:
        for order in uncertain_orders:
            order["status"] = "resolved_via_reconciliation"
            resolved_orders.append(order)
        uncertain_orders.clear()

    return {
        "status": "reconciled",
        "venue_id": venue_id,
        "uncertain_count": len(uncertain_orders),
        "resolved_count": len(resolved_orders),
        "uncertain_orders": uncertain_orders,
        "timestamp_ns": time.time_ns(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile uncertain orders from event journal")
    parser.add_argument("--journal", type=Path, default=Path("build/journal.jsonl"))
    parser.add_argument("--venue-id", type=str, default="exchange-a-sim")
    parser.add_argument("--auto-resolve", action="store_true")
    args = parser.parse_args()

    result = reconcile_orders(args.journal, args.venue_id, args.auto_resolve)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "reconciled" else 1


if __name__ == "__main__":
    sys.exit(main())
