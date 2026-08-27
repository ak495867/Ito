from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path


class ProvenanceError(RuntimeError):
    pass


def source_digest(root: Path) -> str:
    hasher = hashlib.sha256()
    excluded = {"build", "target", "_build", ".git", "__pycache__"}
    paths = [
        path
        for path in root.rglob("*")
        if path.is_file() and not any(part in excluded for part in path.parts)
    ]
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        hasher.update(len(relative).to_bytes(4, "big"))
        hasher.update(relative)
        hasher.update(len(payload).to_bytes(8, "big"))
        hasher.update(payload)
    return hasher.hexdigest()


def rust_components(lock_path: Path) -> list[dict[str, str]]:
    try:
        data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ProvenanceError(f"lockfile_invalid:{error}") from error
    components = []
    for package in data.get("package", []):
        if (
            not isinstance(package, dict)
            or not isinstance(package.get("name"), str)
            or not isinstance(package.get("version"), str)
        ):
            raise ProvenanceError("package_invalid")
        component = {"name": package["name"], "version": package["version"]}
        if isinstance(package.get("source"), str):
            component["source"] = package["source"]
        if isinstance(package.get("checksum"), str):
            component["checksum"] = package["checksum"]
        components.append(component)
    return sorted(components, key=lambda item: (item["name"], item["version"]))


def build_document(root: Path) -> dict[str, object]:
    lockfile = root / "rust/Cargo.lock"
    if not lockfile.is_file():
        raise ProvenanceError("lockfile_missing")
    return {
        "format": 1,
        "type": "ito-release-provenance",
        "source_sha256": source_digest(root),
        "components": rust_components(lockfile),
        "system_dependencies": ["c++20", "openssl", "ocaml", "iverilog", "python3"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = build_document(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("provenance_generated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProvenanceError as error:
        raise SystemExit(str(error))
