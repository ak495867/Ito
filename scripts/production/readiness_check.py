from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate(matrix: dict[str, object]) -> dict[str, object]:
    gates = matrix.get("gates", [])
    implemented = [gate for gate in gates if gate.get("implemented")]
    blockers = [gate for gate in gates if not gate.get("implemented")]
    return {"system": matrix.get("system", "Ito"), "status": "production_ready" if not blockers else "not_production_ready", "implemented_count": len(implemented), "gate_count": len(gates), "blocker_count": len(blockers), "blockers": [{"id": gate.get("id"), "domain": gate.get("domain"), "name": gate.get("name"), "evidence": gate.get("evidence")} for gate in blockers]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=Path("docs/production/readiness_matrix.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.matrix.read_text(encoding="utf-8")))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "production_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
