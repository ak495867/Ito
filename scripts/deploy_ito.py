from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


class DeploymentError(RuntimeError):
    pass


def run(command: list[str], execute: bool) -> None:
    print("$ " + " ".join(command))
    if not execute:
        return
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise DeploymentError(f"command_failed:{result.returncode}")


def inventory(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("nodes"), list):
        raise DeploymentError("invalid_inventory")
    return value


def compose_command(context: str, compose_file: str, project: str, action: str) -> list[str]:
    base = ["docker", "--context", context, "compose", "-p", project, "-f", compose_file]
    if action == "up":
        return base + ["up", "-d", "--remove-orphans"]
    if action == "down":
        return base + ["down", "--remove-orphans"]
    if action == "status":
        return base + ["ps"]
    raise DeploymentError(f"unsupported_action:{action}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", default="infra/docker/branch-nodes.json")
    parser.add_argument("--action", choices=("plan", "build", "deploy", "status", "down"), default="plan")
    parser.add_argument("--node", action="append")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--tag")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    data = inventory(root / args.inventory)
    compose_file = str(root / str(data["compose_file"]))
    image = args.tag or str(data.get("image", "ito:local"))
    nodes = data["nodes"]
    if any(not isinstance(node, dict) or not isinstance(node.get("node_id"), str) or not isinstance(node.get("branch_id"), int) or not isinstance(node.get("entity_id"), int) or node.get("branch_id") <= 0 or node.get("entity_id") <= 0 or node.get("mode", "restricted") not in {"restricted", "lab"} for node in nodes):
        raise DeploymentError("inventory_node_invalid")
    selected = [node for node in nodes if not args.node or node.get("node_id") in args.node]
    if not selected:
        raise DeploymentError("no_nodes_selected")

    if args.action in ("plan", "build"):
        run(["docker", "build", "-t", image, "-f", str(root / "infra/docker/Dockerfile"), str(root)], args.execute)
    if args.action == "build":
        return 0

    for node in selected:
        node_id = str(node["node_id"])
        context = str(node["docker_context"])
        project = f"ito-{node_id}"
        environment = os.environ.copy()
        environment["ITO_BRANCH_ID"] = str(node["branch_id"])
        environment["ITO_ENTITY_ID"] = str(node["entity_id"])
        environment["ITO_MODE"] = str(node.get("mode", "restricted"))
        if environment["ITO_MODE"] not in {"restricted", "lab"}:
            raise DeploymentError(f"unsupported_mode:{node_id}")
        print(f"node={node_id} branch={environment['ITO_BRANCH_ID']} mode={environment['ITO_MODE']}")
        command = compose_command(context, compose_file, project, {"deploy": "up", "status": "status", "down": "down"}.get(args.action, "status"))
        if args.execute:
            result = subprocess.run(command, check=False, env=environment)
            if result.returncode != 0:
                raise DeploymentError(f"command_failed:{node_id}:{result.returncode}")
        else:
            print("$ " + " ".join(command))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DeploymentError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
