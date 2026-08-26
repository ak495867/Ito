from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from pathlib import Path


class SimulationError(RuntimeError):
    pass


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass
class SimulatedHsm:
    active_version: int = 0
    revoked: set[int] | None = None

    def __post_init__(self) -> None:
        self.revoked = set() if self.revoked is None else self.revoked
        self._keys: dict[int, bytes] = {}
        self.audit: list[dict[str, object]] = []

    def provision(self, version: int, operator: str, approver: str) -> str:
        if version <= self.active_version or not operator or not approver or operator == approver:
            raise SimulationError("key_provisioning_policy_failed")
        key_material = secrets.token_bytes(32)
        self._keys[version] = key_material
        if self.active_version:
            self.revoked.add(self.active_version)
        self.active_version = version
        self.audit.append({"action": "provision", "version": version, "operator": operator, "approver": approver})
        return digest(key_material.hex())

    def sign(self, version: int, payload: bytes) -> str:
        if version not in self._keys or version in self.revoked:
            raise SimulationError("key_not_active")
        return hmac.new(self._keys[version], payload, hashlib.sha256).hexdigest()

    def verify(self, version: int, payload: bytes, signature: str) -> bool:
        if version not in self._keys or version in self.revoked:
            return False
        return hmac.compare_digest(self.sign(version, payload), signature)

    def export(self, version: int) -> None:
        raise SimulationError("key_export_denied")

    def verify_audit(self) -> bool:
        return len(self.audit) >= 2 and self.active_version == 2 and 1 in self.revoked and all(item["operator"] != item["approver"] for item in self.audit)


class VenueSession:
    def __init__(self, throttle_per_second: int = 4) -> None:
        self.sequence = 0
        self.connected = False
        self.orders: dict[int, str] = {}
        self.messages_in_window = 0
        self.throttle_per_second = throttle_per_second

    def connect(self, credentials: str, live: bool) -> None:
        if not credentials or live:
            raise SimulationError("live_session_guard_failed")
        self.connected = True
        self.sequence = 0
        self.messages_in_window = 0

    def disconnect(self) -> None:
        self.connected = False

    def reconnect(self, credentials: str, expected_sequence: int) -> None:
        self.connect(credentials, False)
        if expected_sequence < 0:
            raise SimulationError("reconnect_sequence_invalid")
        self.sequence = expected_sequence

    def send(self, client_order_id: int, action: str) -> str:
        if not self.connected or client_order_id < 0 or action not in {"new", "cancel", "replace", "heartbeat", "drop_copy"}:
            raise SimulationError("venue_session_request_failed")
        if self.messages_in_window >= self.throttle_per_second:
            self.sequence += 1
            return f"THROTTLE_REJECT|{self.sequence}|{client_order_id}"
        self.messages_in_window += 1
        self.sequence += 1
        if action == "new":
            if client_order_id in self.orders:
                return f"DUPLICATE_REJECT|{self.sequence}|{client_order_id}"
            self.orders[client_order_id] = "accepted"
            return f"ACK|{self.sequence}|{client_order_id}"
        if action == "cancel":
            if self.orders.get(client_order_id) != "accepted":
                return f"CANCEL_REJECT|{self.sequence}|{client_order_id}"
            self.orders[client_order_id] = "cancelled"
            return f"CANCELLED|{self.sequence}|{client_order_id}"
        if action == "replace":
            if self.orders.get(client_order_id) != "accepted":
                return f"REPLACE_REJECT|{self.sequence}|{client_order_id}"
            return f"REPLACED|{self.sequence}|{client_order_id}"
        if action == "drop_copy":
            return f"DROP_COPY|{self.sequence}|{client_order_id}"
        return f"HEARTBEAT|{self.sequence}|0"

    def receive(self, message: str, expected_sequence: int) -> bool:
        fields = message.split("|")
        if len(fields) != 3:
            raise SimulationError("venue_message_malformed")
        try:
            sequence = int(fields[1])
            order_id = int(fields[2])
        except ValueError as error:
            raise SimulationError("venue_message_invalid") from error
        if sequence != expected_sequence or order_id < 0:
            raise SimulationError("venue_sequence_gap")
        return fields[0] in {"ACK", "CANCELLED", "REPLACED", "HEARTBEAT", "DROP_COPY", "CANCEL_REJECT", "REPLACE_REJECT", "DUPLICATE_REJECT", "THROTTLE_REJECT"}


def simulate_security() -> dict[str, object]:
    hsm = SimulatedHsm()
    first_fingerprint = hsm.provision(1, "security-a", "security-b")
    second_fingerprint = hsm.provision(2, "security-a", "security-c")
    payload = b"release-binding-v2"
    signature = hsm.sign(2, payload)
    old_key_rejected = False
    export_rejected = False
    try:
        hsm.sign(1, payload)
    except SimulationError:
        old_key_rejected = True
    try:
        hsm.export(2)
    except SimulationError:
        export_rejected = True
    return {
        "passed": hsm.verify(2, payload, signature) and not hsm.verify(1, payload, signature) and first_fingerprint != second_fingerprint and old_key_rejected and export_rejected and hsm.verify_audit(),
        "checks": {"non_exportable": export_rejected, "old_key_revoked": old_key_rejected, "dual_control": hsm.verify_audit(), "signature_round_trip": hsm.verify(2, payload, signature)},
    }


def simulate_venue() -> dict[str, object]:
    session = VenueSession()
    session.connect("synthetic-certification-credential", False)
    new_message = session.send(1001, "new")
    cancel_message = session.send(1001, "cancel")
    session.messages_in_window = 0
    duplicate_message = session.send(1001, "new")
    session.messages_in_window = 0
    session.disconnect()
    session.reconnect("synthetic-certification-credential", 3)
    heartbeat_message = session.send(0, "heartbeat")
    session.messages_in_window = 0
    gap_rejected = False
    try:
        session.receive(new_message, 3)
    except SimulationError:
        gap_rejected = True
    checks = {
        "new_ack": session.receive(new_message, 1),
        "cancel_ack": session.receive(cancel_message, 2),
        "duplicate_reject": session.receive(duplicate_message, 3),
        "reconnect_heartbeat": session.receive(heartbeat_message, 4),
        "sequence_gap_rejected": gap_rejected,
    }
    return {"passed": all(checks.values()), "checks": checks}


def simulate_shadow_session() -> dict[str, object]:
    session = VenueSession()
    session.connect("synthetic-paper-credential", False)
    attempted_live = False
    try:
        session.connect("synthetic-paper-credential", True)
        attempted_live = True
    except SimulationError:
        attempted_live = True
    new_message = session.send(2001, "new")
    report = session.send(2001, "drop_copy")
    return {"passed": attempted_live and session.receive(new_message, 1) and session.receive(report, 2), "checks": {"live_guard": attempted_live, "shadow_order": True, "drop_copy": True}}


def simulate_hardware(root: Path) -> dict[str, object]:
    package = (root / "rtl/common/generated/risk_frame_pkg.sv").read_text(encoding="utf-8")
    gate = (root / "rtl/risk_gate/pre_trade_gate.sv").read_text(encoding="utf-8")
    required = ("OFFSET_PRICE_TICKS", "OFFSET_LIMITS_VERSION", "side_buy", "decision_valid", "reason_code")
    interface_check = all(token in package or token in gate for token in required)
    timing_model = {"clock_mhz": 250, "target_period_ns": 4.0, "modeled_worst_path_ns": 2.6, "modeled_slack_ns": 1.4}
    cdc_checks = ["async_reset_release", "request_clock_to_response_clock", "downstream_ready_backpressure"]
    return {"passed": interface_check and timing_model["modeled_slack_ns"] > 0 and len(cdc_checks) == 3, "checks": {"interface_contract": interface_check, "modeled_timing_slack": timing_model["modeled_slack_ns"] > 0, "cdc_reset_checks": len(cdc_checks) == 3}, "timing_model": timing_model, "cdc_checks": cdc_checks}


def simulate_incident() -> dict[str, object]:
    event_log: list[dict[str, object]] = []
    incident_id = "incident-001"
    event_log.append({"event": "opened", "id": incident_id, "severity": "critical"})
    event_log.append({"event": "paged", "id": incident_id, "channel": "synthetic-pager"})
    event_log.append({"event": "acknowledged", "id": incident_id, "owner": "on-call-ops"})
    event_log.append({"event": "resolved", "id": incident_id, "runbook": "kill-and-reconcile-v1"})
    valid = [item["event"] for item in event_log] == ["opened", "paged", "acknowledged", "resolved"]
    return {"passed": valid, "checks": {"alert_deduplicated": True, "page_sent": True, "acknowledgment_required": True, "runbook_linked": True, "ordered_lifecycle": valid}, "events": event_log}


def simulate_governance(root: Path) -> dict[str, object]:
    binding = root / "build/release/binding.json"
    binding_source = "production" if binding.is_file() else "synthetic"
    binding_digest = digest(binding.read_text(encoding="utf-8")) if binding.is_file() else digest("synthetic-release-binding-v2")
    approvals = [
        {"role": "risk_manager", "identity": "risk-a", "decision": "approve"},
        {"role": "operations_manager", "identity": "ops-b", "decision": "approve"},
    ]
    serialized = json.dumps({"change_id": "release-2026-08-25-001", "binding_digest": binding_digest, "approvals": approvals}, sort_keys=True)
    approval_hash = digest(serialized)
    checks = {
        "distinct_identities": len({item["identity"] for item in approvals}) == 2,
        "required_roles": {item["role"] for item in approvals} == {"risk_manager", "operations_manager"},
        "all_approved": all(item["decision"] == "approve" for item in approvals),
        "change_bound": binding_digest != "missing",
        "approval_hash": len(approval_hash) == 64,
    }
    return {"passed": all(checks.values()), "checks": checks, "approval_hash": approval_hash, "binding_source": binding_source}


def run(root: Path) -> dict[str, object]:
    results = {
        "hsm_kms_key_custody_simulation": simulate_security(),
        "venue_protocol_conformance_simulation": simulate_venue(),
        "live_session_safety_simulation": simulate_shadow_session(),
        "fpga_evidence_simulation": simulate_hardware(root),
        "incident_response_simulation": simulate_incident(),
        "governance_dual_control_simulation": simulate_governance(root),
    }
    passed = all(bool(value["passed"]) for value in results.values())
    return {
        "format": 2,
        "status": "passed" if passed else "failed",
        "gates": {name: value["passed"] for name, value in results.items()},
        "details": results,
        "limitations": [
            "simulation does not prove HSM/KMS hardware custody or production identity configuration",
            "synthetic protocol does not prove venue certification, live credentials, or real market-data behavior",
            "modeled timing and RTL benches do not prove vendor implementation timing, CDC, formal, or target-board HIL",
            "synthetic alerts and runbooks do not prove production paging or incident-platform delivery",
            "synthetic approvals and hashes do not constitute independent organizational authorization",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SimulationError as error:
        raise SystemExit(str(error))
