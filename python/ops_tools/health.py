from __future__ import annotations

import json
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class HealthSnapshot:
    branch_id: str
    feed_healthy: bool
    clock_healthy: bool
    gateway_ready: bool
    journal_ready: bool
    policy_valid: bool

    @property
    def trading_allowed(self) -> bool:
        return all((self.feed_healthy, self.clock_healthy, self.gateway_ready, self.journal_ready, self.policy_valid))

    def as_dict(self) -> dict[str, object]:
        return {"branch_id": self.branch_id, "trading_allowed": self.trading_allowed, "feed_healthy": self.feed_healthy, "clock_healthy": self.clock_healthy, "gateway_ready": self.gateway_ready, "journal_ready": self.journal_ready, "policy_valid": self.policy_valid}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 health.py <snapshot.json>", file=sys.stderr)
        return 2
    snapshot = json.loads(open(sys.argv[1], encoding="utf-8").read())
    result = HealthSnapshot(str(snapshot["branch_id"]), bool(snapshot["feed_healthy"]), bool(snapshot["clock_healthy"]), bool(snapshot["gateway_ready"]), bool(snapshot["journal_ready"]), bool(snapshot["policy_valid"]))
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 0 if result.trading_allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
