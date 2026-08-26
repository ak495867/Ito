from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare(local: list[dict[str, object]], venue: list[dict[str, object]]) -> list[dict[str, object]]:
    local_by_id = {int(item["client_order_id"]): item for item in local}
    venue_by_id = {int(item["client_order_id"]): item for item in venue}
    findings: list[dict[str, object]] = []
    for client_order_id, order in local_by_id.items():
        report = venue_by_id.get(client_order_id)
        if report is None:
            findings.append({"client_order_id": client_order_id, "state": "missing_venue", "detail": "venue_report_missing"})
        elif int(report.get("executed_quantity", 0)) < int(order.get("executed_quantity", 0)):
            findings.append({"client_order_id": client_order_id, "state": "quantity_mismatch", "detail": "venue_quantity_below_local"})
        elif int(order.get("average_price_ticks", 0)) and int(report.get("average_price_ticks", 0)) != int(order.get("average_price_ticks", 0)):
            findings.append({"client_order_id": client_order_id, "state": "price_mismatch", "detail": "average_price_differs"})
        else:
            findings.append({"client_order_id": client_order_id, "state": "matched", "detail": "matched"})
    for client_order_id in venue_by_id:
        if client_order_id not in local_by_id:
            findings.append({"client_order_id": client_order_id, "state": "missing_local", "detail": "local_order_missing"})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("local", type=Path)
    parser.add_argument("venue", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    local = json.loads(args.local.read_text(encoding="utf-8"))
    venue = json.loads(args.venue.read_text(encoding="utf-8"))
    findings = compare(local, venue)
    result = {"findings": findings, "ambiguous": any(item["state"] != "matched" for item in findings)}
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
