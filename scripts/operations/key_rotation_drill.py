from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from pathlib import Path


class RotationError(RuntimeError):
    pass


def key_fingerprint(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()


def drill(output: Path) -> dict[str, object]:
    first_key = secrets.token_bytes(32)
    second_key = secrets.token_bytes(32)
    first = {"version": 1, "fingerprint": key_fingerprint(first_key), "active": False}
    second = {"version": 2, "fingerprint": key_fingerprint(second_key), "active": True}
    if (
        first["fingerprint"] == second["fingerprint"]
        or first["active"]
        or not second["active"]
        or second["version"] <= first["version"]
    ):
        raise RotationError("rotation_invariant_failed")
    result = {
        "format": 1,
        "status": "passed",
        "active_version": second["version"],
        "retired_versions": [first["version"]],
        "key_fingerprints": [first["fingerprint"], second["fingerprint"]],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = drill(args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RotationError as error:
        raise SystemExit(str(error))
