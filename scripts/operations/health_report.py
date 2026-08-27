from __future__ import annotations

import argparse
import json
from pathlib import Path


class HealthError(RuntimeError):
    pass


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HealthError(f"invalid_json:{path}:{error}") from error


def build_report(readiness_path: Path, recovery_path: Path) -> dict[str, object]:
    readiness = load_json(readiness_path)
    if not isinstance(readiness, dict):
        raise HealthError("invalid_readiness")
    local_ids = {
        "GATE-SW-001",
        "GATE-SW-002",
        "GATE-SW-003",
        "GATE-SW-004",
        "GATE-HW-001",
        "GATE-OPS-001",
        "GATE-SEC-003",
        "GATE-SEC-004",
        "GATE-OPS-003",
        "GATE-OPS-004",
        "GATE-OPS-005",
    }
    if isinstance(readiness.get("gates"), list):
        gates = readiness["gates"]
        local_failures = [
            str(gate.get("id"))
            for gate in gates
            if isinstance(gate, dict)
            and gate.get("id") in local_ids
            and gate.get("implemented") is not True
        ]
        blockers = [
            str(gate.get("id"))
            for gate in gates
            if isinstance(gate, dict) and gate.get("implemented") is not True
        ]
    elif isinstance(readiness.get("blockers"), list):
        blockers = [
            str(gate.get("id"))
            for gate in readiness["blockers"]
            if isinstance(gate, dict)
        ]
        local_failures = [
            identifier for identifier in blockers if identifier in local_ids
        ]
    else:
        raise HealthError("invalid_readiness")
    return {
        "format": 1,
        "local_status": (
            "healthy" if not local_failures and recovery_path.is_file() else "degraded"
        ),
        "production_status": str(readiness.get("status", "unknown")),
        "local_failures": local_failures,
        "external_blockers": blockers,
        "external_blocker_count": len(blockers),
        "recovery_artifact_present": recovery_path.is_file(),
    }


def write_prometheus(report: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    local_status = 1 if report["local_status"] == "healthy" else 0
    production_status = 1 if report["production_status"] == "production_ready" else 0
    recovery = 1 if report["recovery_artifact_present"] else 0
    path.write_text(
        "\n".join(
            (
                "# HELP ito_local_validation_pass Local repository controls and recovery artifact passed",
                "# TYPE ito_local_validation_pass gauge",
                f"ito_local_validation_pass {local_status}",
                "# HELP ito_production_readiness Production readiness gate passed",
                "# TYPE ito_production_readiness gauge",
                f"ito_production_readiness {production_status}",
                "# HELP ito_external_blocker_count Unresolved external production gates",
                "# TYPE ito_external_blocker_count gauge",
                f"ito_external_blocker_count {report['external_blocker_count']}",
                "# HELP ito_recovery_artifact_present Manifest-verified recovery artifact present",
                "# TYPE ito_recovery_artifact_present gauge",
                f"ito_recovery_artifact_present {recovery}",
                "",
            )
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--recovery", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prometheus", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.readiness, args.recovery)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_prometheus(report, args.prometheus)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HealthError as error:
        raise SystemExit(str(error))
