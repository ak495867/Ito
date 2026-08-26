from __future__ import annotations

import argparse
import json
from pathlib import Path


def aggregate(sessions: list[dict[str, object]]) -> dict[str, object]:
    ready = [item for item in sessions if item.get("status") == "ready"]
    degraded = [item for item in sessions if item.get("status") != "ready"]
    return {"session_count": len(sessions), "ready_count": len(ready), "degraded_count": len(degraded), "execution_enabled": bool(sessions) and not degraded and len(ready) == len(sessions), "venues": sessions}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sessions = json.loads(args.input.read_text(encoding="utf-8"))
    result = aggregate(sessions)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
