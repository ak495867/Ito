from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_hardware_response.py <response.json>", file=sys.stderr)
        return 2
    response = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    frame_hex = str(response["frame_hex"])
    decision = response["response"]["decision"]
    if len(frame_hex) != 128 or len(frame_hex) % 2 != 0:
        print("frame_size_invalid", file=sys.stderr)
        return 1
    if decision != "Approved":
        print("decision_invalid", file=sys.stderr)
        return 1
    print("hardware_response_valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
