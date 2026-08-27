from __future__ import annotations

import argparse
import json
from pathlib import Path


def recommend(
    routes: list[dict[str, object]],
    sessions: list[dict[str, object]],
    quantity: int,
    live: bool = False,
) -> list[dict[str, object]]:
    if quantity <= 0:
        return []
    state = {int(item["venue_id"]): str(item["status"]) for item in sessions}
    selected = []
    for route in routes:
        venue_id = int(route["venue_id"])
        live_enabled = route.get("live_enabled")
        if (
            not route.get("enabled")
            or (live and live_enabled is not True)
            or (not live and live_enabled is not False)
        ):
            continue
        if state.get(venue_id) != "ready":
            continue
        if quantity > int(route.get("max_order_quantity", 0)):
            continue
        selected.append(route)
    return sorted(
        selected,
        key=lambda item: (
            int(item.get("rank", 0)),
            int(item.get("fee_bps", 0)),
            int(item["venue_id"]),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("routes", type=Path)
    parser.add_argument("sessions", type=Path)
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    route_data = json.loads(args.routes.read_text(encoding="utf-8"))
    session_data = json.loads(args.sessions.read_text(encoding="utf-8"))
    print(
        json.dumps(
            recommend(route_data["routes"], session_data, args.quantity, args.live),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
