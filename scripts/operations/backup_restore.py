from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path


class BackupError(RuntimeError):
    pass


DEFAULT_PATHS = (
    "config",
    "interfaces",
    "infra",
    "docs/production/readiness_matrix.json",
)


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise BackupError(f"unsafe_path:{value}")
    return path


def relative_path(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        root_name = os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(root))))
        path_name = os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))
        relative = Path(os.path.relpath(path_name, root_name))
    if (
        relative.is_absolute()
        or relative == Path(os.pardir)
        or relative.parts[:1] == (os.pardir,)
    ):
        raise BackupError(f"outside_root:{path}")
    return relative.as_posix()


def ensure_within_root(root: Path, path: Path) -> None:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    current = resolved_path
    try:
        while True:
            if os.path.samefile(current, resolved_root):
                return
            parent = current.parent
            if parent == current:
                break
            current = parent
    except OSError:
        pass
    raise BackupError(f"outside_root:{path}")


def collect(root: Path, requested: list[str]) -> list[Path]:
    files: set[Path] = set()
    for value in requested or list(DEFAULT_PATHS):
        relative = safe_relative(value)
        candidate = root / relative
        if not candidate.exists():
            raise BackupError(f"missing_path:{value}")
        ensure_within_root(root, candidate)
        if candidate.is_symlink():
            raise BackupError(f"unsupported_source:{value}")
        if candidate.is_file():
            files.add(candidate)
        else:
            files.update(
                path
                for path in candidate.rglob("*")
                if path.is_file() and not path.is_symlink()
            )
    return sorted(files)


def manifest(root: Path, files: list[Path]) -> dict[str, object]:
    entries = []
    for path in files:
        relative = relative_path(root, path)
        entries.append(
            {"path": relative, "size": path.stat().st_size, "sha256": digest(path)}
        )
    return {"format": 1, "root": root.name, "files": entries}


def backup(root: Path, output: Path, requested: list[str]) -> None:
    files = collect(root, requested)
    data = manifest(root, files)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", dir=output.parent
    )
    os.close(descriptor)
    try:
        with tarfile.open(temporary_name, "w:gz") as archive:
            payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
            info = tarfile.TarInfo("manifest.json")
            info.size = len(payload)
            archive.addfile(info, __import__("io").BytesIO(payload))
            for path in files:
                archive.add(path, arcname=relative_path(root, path), recursive=False)
        os.replace(temporary_name, output)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def verify_members(archive: tarfile.TarFile) -> None:
    for member in archive.getmembers():
        relative = safe_relative(member.name)
        if relative == Path("manifest.json"):
            if not member.isfile() or member.issym() or member.islnk():
                raise BackupError(f"unsupported_member:{member.name}")
            continue
        if not member.isfile() or member.issym() or member.islnk():
            raise BackupError(f"unsupported_member:{member.name}")


def restore(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        verify_members(archive)
        manifest_member = archive.getmember("manifest.json")
        data = json.load(archive.extractfile(manifest_member))
        if data.get("format") != 1 or not isinstance(data.get("files"), list):
            raise BackupError("invalid_manifest")
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            staging = Path(temporary)
            archive.extractall(staging, filter="data")
            for entry in data["files"]:
                relative = safe_relative(str(entry["path"]))
                source = staging / relative
                if (
                    not source.is_file()
                    or source.stat().st_size != int(entry["size"])
                    or digest(source) != entry["sha256"]
                ):
                    raise BackupError(f"integrity_failure:{relative.as_posix()}")
            for entry in data["files"]:
                relative = safe_relative(str(entry["path"]))
                source = staging / relative
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary_target = target.with_name(f".{target.name}.restore")
                shutil.copyfile(source, temporary_target)
                os.replace(temporary_target, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--root", type=Path, default=Path("."))
    backup_parser.add_argument("--output", type=Path, required=True)
    backup_parser.add_argument("--path", action="append", dest="paths")
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--archive", type=Path, required=True)
    restore_parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "backup":
        backup(args.root.resolve(), args.output.resolve(), args.paths or [])
    else:
        restore(args.archive.resolve(), args.destination.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BackupError, OSError, tarfile.TarError, ValueError, KeyError) as error:
        raise SystemExit(str(error))
