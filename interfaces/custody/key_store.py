from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import new as hmac_new
from typing import Protocol


@dataclass(frozen=True)
class KeyVersion:
    key_id: str
    version: int
    active: bool
    exportable: bool


class KeyStore(Protocol):
    def active_key(self, key_id: str) -> KeyVersion: ...
    def rotate(self, key_id: str) -> KeyVersion: ...
    def revoke(self, key_id: str, version: int) -> None: ...


class InMemoryKeyStore:
    def __init__(self) -> None:
        self._keys: dict[str, list[KeyVersion]] = {}

    def active_key(self, key_id: str) -> KeyVersion:
        versions = self._keys.get(key_id, [])
        for version in reversed(versions):
            if version.active:
                return version
        return self.rotate(key_id)

    def rotate(self, key_id: str) -> KeyVersion:
        if not key_id:
            raise ValueError("key_id_invalid")
        versions = self._keys.setdefault(key_id, [])
        self._keys[key_id] = [
            KeyVersion(item.key_id, item.version, False, item.exportable)
            for item in versions
        ]
        next_version = len(versions) + 1
        value = KeyVersion(key_id, next_version, True, False)
        self._keys[key_id].append(value)
        return value

    def revoke(self, key_id: str, version: int) -> None:
        versions = self._keys.get(key_id, [])
        if not any(item.version == version for item in versions):
            raise KeyError("key_version_missing")
        self._keys[key_id] = [
            KeyVersion(item.key_id, item.version, False, item.exportable)
            if item.version == version
            else item
            for item in versions
        ]


class Signer(Protocol):
    def sign(self, key_id: str, payload: bytes) -> bytes: ...
    def verify(self, key_id: str, payload: bytes, signature: bytes) -> bool: ...


class HmacSimulatorSigner:
    def __init__(self, key_store: InMemoryKeyStore | None = None) -> None:
        self.key_store = key_store or InMemoryKeyStore()
        self._secrets: dict[tuple[str, int], bytes] = {}

    def _secret(self, key_id: str, version: int) -> bytes:
        key = (key_id, version)
        if key not in self._secrets:
            self._secrets[key] = sha256(f"simulator:{key_id}:{version}".encode()).digest()
        return self._secrets[key]

    def sign(self, key_id: str, payload: bytes) -> bytes:
        active = self.key_store.active_key(key_id)
        return hmac_new(self._secret(key_id, active.version), payload, "sha256").digest()

    def verify(self, key_id: str, payload: bytes, signature: bytes) -> bool:
        versions = self.key_store._keys.get(key_id, [])
        for version in versions:
            if hmac_new(self._secret(key_id, version.version), payload, "sha256").digest() == signature:
                return True
        return False
