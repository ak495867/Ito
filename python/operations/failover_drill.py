from __future__ import annotations

import argparse
import json
from pathlib import Path


def drill(lease: dict[str, object], findings: list[dict[str, object]]) -> dict[str, object]:
    owner = str(lease.get("owner_id", ""))
    epoch = int(lease.get("epoch", 0))
    expired = int(lease.get("expires_at_ns", 0)) <= int(lease.get("now_ns", 0))
    ambiguous = any(item.get("state") != "matched" for item in findings)
    promoted = bool(owner) and epoch > 0 and not expired and not ambiguous
    return {"previous_owner": owner, "previous_epoch": epoch, "expired": expired, "ambiguous": ambiguous, "promoted": promoted, "action": "promote_standby" if promoted else "hold_and_escalate"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lease", type=Path, required=True)
    parser.add_argument("--findings", type=Path, required=True)
    args = parser.parse_args()
    lease = json.loads(args.lease.read_text(encoding="utf-8"))
    findings = json.loads(args.findings.read_text(encoding="utf-8"))["findings"]
    print(json.dumps(drill(lease, findings), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
