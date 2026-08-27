from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path


class EvidenceError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(root: Path) -> dict[str, object]:
    snapshot = json.loads(
        (root / "build/portfolio/snapshot.json").read_text(encoding="utf-8")
    )
    expected = {
        "net_position": 6,
        "gross_position": 6,
        "gross_notional_ticks": 690,
        "realized_pnl_ticks": 80,
        "unrealized_pnl_ticks": 90,
        "loss_ticks": -170,
    }
    pnl_checks = {name: snapshot.get(name) == value for name, value in expected.items()}
    if not all(pnl_checks.values()):
        raise EvidenceError("portfolio_pnl_mismatch")
    if any(snapshot["limits_breached"].values()):
        raise EvidenceError("portfolio_limit_breach")
    archive = root / "build/recovery/ito-config.tar.gz"
    with tarfile.open(archive, "r:gz") as handle:
        manifest = json.loads(
            handle.extractfile("manifest.json").read().decode("utf-8")
        )
    recovery_checks: dict[str, bool] = {}
    for item in manifest["files"]:
        relative = Path(item["path"])
        source = root / relative
        restored = root / "build/recovery/restored" / relative
        source_hash = sha256(source)
        restored_hash = sha256(restored)
        recovery_checks[str(relative)] = (
            source_hash == item["sha256"] == restored_hash
            and source.stat().st_size == item["size"]
            and restored.stat().st_size == item["size"]
        )
    if not all(recovery_checks.values()):
        raise EvidenceError("recovery_manifest_mismatch")
    return {
        "portfolio": {
            "checks": pnl_checks,
            "limits_breached": snapshot["limits_breached"],
            "status": "passed",
        },
        "recovery": {
            "manifest_format": manifest["format"],
            "files": recovery_checks,
            "status": "passed",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceError as error:
        raise SystemExit(str(error))
