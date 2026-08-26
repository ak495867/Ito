from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object_required:{path}")
    return value


def validate_profiles(paths: list[Path]) -> list[str]:
    errors: list[str] = []
    venue_ids: set[int] = set()
    broker_ids: set[int] = set()
    for path in paths:
        value = load(path)
        identifier = value.get("venue_id", value.get("broker_id"))
        if not isinstance(identifier, int) or identifier <= 0:
            errors.append(f"identifier_invalid:{path}")
        if "venue_id" in value:
            if value["venue_id"] in venue_ids:
                errors.append(f"duplicate_venue:{value['venue_id']}")
            venue_ids.add(value["venue_id"])
        if "broker_id" in value and "venue_id" not in value:
            if value["broker_id"] in broker_ids:
                errors.append(f"duplicate_broker:{value['broker_id']}")
            broker_ids.add(value["broker_id"])
        for field in ("name", "protocol", "endpoint"):
            if not isinstance(value.get(field), str) or not value[field]:
                errors.append(f"field_invalid:{path}:{field}")
        if value.get("live_enabled") is not False:
            errors.append(f"live_must_be_disabled:{path}")
        if not isinstance(value.get("tls_required"), bool) or value["tls_required"] is not True:
            errors.append(f"tls_required:{path}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    paths = [root / "config/exchanges/exchange-a-sim.json", root / "config/exchanges/exchange-b-sim.json", root / "config/brokers/broker-a-sim.json", root / "config/brokers/broker-b-sim.json"]
    errors = validate_profiles(paths)
    matrix = load(root / "config/routing/adapter_matrix.json")
    adapters = matrix.get("adapters", [])
    adapter_ids = [item.get("adapter_id") for item in adapters]
    if len(adapter_ids) != len(set(adapter_ids)):
        errors.append("duplicate_adapter_id")
    adapter_venue_ids = [item.get("venue_id") for item in adapters]
    if any(not isinstance(value, int) or value <= 0 for value in adapter_venue_ids):
        errors.append("adapter_venue_invalid")
    if len(adapter_venue_ids) != len(set(adapter_venue_ids)):
        errors.append("duplicate_adapter_venue_id")
    if any(item.get("live_enabled") is not False for item in adapters):
        errors.append("adapter_live_must_be_disabled")
    if set(matrix.get("language_ownership", {})) != {"cpp", "rust", "ocaml", "systemverilog", "python"}:
        errors.append("language_ownership_incomplete")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"connectivity_profiles_valid:{len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
