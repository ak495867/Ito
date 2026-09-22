from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path


class HSMError(RuntimeError):
    pass


@dataclass(frozen=True)
class KeyMetadata:
    key_id: str
    algorithm: str
    created_ns: int
    last_used_ns: int = 0
    rotation_count: int = 0
    disabled: bool = False


class HSMSimulator:
    """Deterministic HSM/KMS simulator for development and replay."""

    def __init__(self, master_key: bytes | None = None) -> None:
        self._master_key = master_key or secrets.token_bytes(32)
        self._keys: dict[str, bytes] = {}
        self._metadata: dict[str, KeyMetadata] = {}
        self._audit: list[dict[str, object]] = []
        self._sequence = 0

    def create_key(self, key_id: str, algorithm: str = "AES-256-GCM") -> KeyMetadata:
        if not key_id or algorithm not in {"AES-256-GCM", "HMAC-SHA256", "ECDSA-P256"}:
            raise HSMError("invalid_key_spec")
        if key_id in self._keys:
            raise HSMError("key_exists")
        key = secrets.token_bytes(32)
        self._keys[key_id] = key
        self._metadata[key_id] = KeyMetadata(key_id, algorithm, time.time_ns())
        self._audit_event("key_create", key_id)
        return self._metadata[key_id]

    def rotate_key(self, key_id: str) -> KeyMetadata:
        if key_id not in self._keys:
            raise HSMError("key_missing")
        old_key = self._keys[key_id]
        new_key = secrets.token_bytes(32)
        self._keys[key_id] = new_key
        metadata = self._metadata[key_id]
        self._metadata[key_id] = KeyMetadata(
            key_id=key_id,
            algorithm=metadata.algorithm,
            created_ns=time.time_ns(),
            last_used_ns=metadata.last_used_ns,
            rotation_count=metadata.rotation_count + 1,
            disabled=metadata.disabled,
        )
        self._audit_event("key_rotate", key_id, old_key)
        return self._metadata[key_id]

    def disable_key(self, key_id: str) -> None:
        if key_id not in self._keys:
            raise HSMError("key_missing")
        self._metadata[key_id].disabled = True
        self._audit_event("key_disable", key_id)

    def encrypt(self, key_id: str, plaintext: bytes, aad: bytes = b"") -> bytes:
        if key_id not in self._keys:
            raise HSMError("key_missing")
        if self._metadata[key_id].disabled:
            raise HSMError("key_disabled")
        key = self._keys[key_id]
        nonce = secrets.token_bytes(12)
        ciphertext = bytearray(nonce)
        for index, byte in enumerate(plaintext):
            ciphertext.append(byte ^ key[(nonce[0] + index) % len(key)])
        tag = hmac.new(key, ciphertext + aad, hashlib.sha256).digest()[:16]
        ciphertext.extend(tag)
        self._metadata[key_id].last_used_ns = time.time_ns()
        self._audit_event("encrypt", key_id)
        return bytes(ciphertext)

    def decrypt(self, key_id: str, ciphertext: bytes, aad: bytes = b"") -> bytes:
        if key_id not in self._keys:
            raise HSMError("key_missing")
        if self._metadata[key_id].disabled:
            raise HSMError("key_disabled")
        if len(ciphertext) < 28:
            raise HSMError("ciphertext_too_short")
        key = self._keys[key_id]
        nonce = ciphertext[:12]
        body = ciphertext[12:-16]
        tag = ciphertext[-16:]
        expected_tag = hmac.new(key, body + aad, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected_tag):
            raise HSMError("integrity_failure")
        plaintext = bytearray()
        for index, byte in enumerate(body):
            plaintext.append(byte ^ key[(nonce[0] + index) % len(key)])
        self._metadata[key_id].last_used_ns = time.time_ns()
        self._audit_event("decrypt", key_id)
        return bytes(plaintext)

    def sign(self, key_id: str, data: bytes) -> bytes:
        if key_id not in self._keys:
            raise HSMError("key_missing")
        if self._metadata[key_id].algorithm != "HMAC-SHA256":
            raise HSMError("algorithm_mismatch")
        key = self._keys[key_id]
        signature = hmac.new(key, data, hashlib.sha256).digest()
        self._metadata[key_id].last_used_ns = time.time_ns()
        self._audit_event("sign", key_id)
        return signature

    def verify(self, key_id: str, data: bytes, signature: bytes) -> bool:
        if key_id not in self._keys:
            raise HSMError("key_missing")
        if self._metadata[key_id].algorithm != "HMAC-SHA256":
            raise HSMError("algorithm_mismatch")
        expected = hmac.new(self._keys[key_id], data, hashlib.sha256).digest()
        self._audit_event("verify", key_id)
        return hmac.compare_digest(expected, signature)

    def _audit_event(self, action: str, key_id: str, old_key: bytes | None = None) -> None:
        self._sequence += 1
        entry: dict[str, object] = {
            "sequence": self._sequence,
            "action": action,
            "key_id": key_id,
            "timestamp_ns": time.time_ns(),
        }
        if old_key is not None:
            entry["old_key_fingerprint"] = hashlib.sha256(old_key).hexdigest()[:16]
        self._audit.append(entry)

    def audit_log(self) -> list[dict[str, object]]:
        return [dict(entry) for entry in self._audit]

    def export_state(self) -> dict[str, object]:
        return {
            "keys": {key_id: metadata.__dict__ for key_id, metadata in self._metadata.items()},
            "audit": self.audit_log(),
        }

    @classmethod
    def import_state(cls, state: dict[str, object]) -> "HSMSimulator":
        simulator = cls()
        for key_id, metadata in state["keys"].items():
            simulator._keys[key_id] = secrets.token_bytes(32)
            simulator._metadata[key_id] = KeyMetadata(
                key_id=key_id,
                algorithm=str(metadata["algorithm"]),
                created_ns=int(metadata["created_ns"]),
                last_used_ns=int(metadata.get("last_used_ns", 0)),
                rotation_count=int(metadata.get("rotation_count", 0)),
                disabled=bool(metadata.get("disabled", False)),
            )
        simulator._audit = [dict(entry) for entry in state.get("audit", [])]
        simulator._sequence = max((int(entry["sequence"]) for entry in simulator._audit), default=0)
        return simulator


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    hsm = HSMSimulator()
    hsm.create_key("dev-key-001", "AES-256-GCM")
    encrypted = hsm.encrypt("dev-key-001", b"ito-development-data")
    decrypted = hsm.decrypt("dev-key-001", encrypted)
    if decrypted != b"ito-development-data":
        raise HSMError("round_trip_failure")
    payload = json.dumps(hsm.export_state(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())