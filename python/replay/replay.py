from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Event:
    event_id: int
    sequence: int
    event_type: str
    correlation_id: int
    payload: str


def load_events(path: Path) -> list[Event]:
    events: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        events.append(
            Event(
                int(raw["event_id"]),
                int(raw["sequence"]),
                str(raw["event_type"]),
                int(raw["correlation_id"]),
                str(raw["payload"]),
            )
        )
    return events


def validate(events: list[Event]) -> list[str]:
    failures: list[str] = []
    expected = 1
    event_ids: set[int] = set()
    for event in events:
        if event.event_id <= 0 or event.correlation_id < 0:
            failures.append(
                f"identifier_invalid:{event.event_id}:{event.correlation_id}"
            )
        if event.event_id in event_ids:
            failures.append(f"duplicate_event_id:{event.event_id}")
        event_ids.add(event.event_id)
        if event.sequence != expected:
            failures.append(f"sequence_gap:{expected}:{event.sequence}")
        expected = event.sequence + 1 if event.sequence >= expected else expected
    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 replay.py <journal.jsonl>", file=sys.stderr)
        return 2
    events = load_events(Path(sys.argv[1]))
    failures = validate(events)
    print(
        json.dumps(
            {"events": len(events), "valid": not failures, "failures": failures},
            sort_keys=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
