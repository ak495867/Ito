from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class BindingError(RuntimeError):
    pass


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify(binding_path: Path, policy_path: Path, rtl_path: Path, schema_path: Path) -> None:
    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BindingError(f"invalid_binding:{error}") from error
    if not isinstance(binding, dict) or not isinstance(binding.get("policy_version"), int) or binding["policy_version"] <= 0:
        raise BindingError("invalid_policy_version")
    paths = (("artifact_digest", policy_path), ("rtl_digest", rtl_path), ("schema_digest", schema_path))
    for field, path in paths:
        expected = binding.get(field)
        if not isinstance(expected, str) or len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            raise BindingError(f"invalid_digest:{field}")
        if not path.is_file() or digest(path) != expected:
            raise BindingError(f"digest_mismatch:{field}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--rtl", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    args = parser.parse_args()
    verify(args.binding, args.policy, args.rtl, args.schema)
    print("release_binding_verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BindingError as error:
        raise SystemExit(str(error))
