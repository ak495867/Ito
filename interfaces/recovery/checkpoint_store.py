from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Checkpoint:
    name: str
    sequence: int
    payload: dict[str, object]
    checksum: str


class CheckpointStore(Protocol):
    def save(self, name: str, sequence: int, payload: dict[str, object]) -> Checkpoint: ...
    def load(self, name: str) -> Checkpoint: ...
    def close(self) -> None: ...


class SQLiteCheckpointStore:
    def __init__(self, path: str | Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints (name TEXT PRIMARY KEY, sequence INTEGER NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL)"
        )
        self.connection.commit()

    def save(self, name: str, sequence: int, payload: dict[str, object]) -> Checkpoint:
        if not name or sequence < 0:
            raise ValueError("checkpoint_metadata_invalid")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        checksum = hashlib.sha256(serialized.encode()).hexdigest()
        with self.connection:
            self.connection.execute(
                "INSERT INTO checkpoints(name, sequence, payload, checksum) VALUES (?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET sequence=excluded.sequence, payload=excluded.payload, checksum=excluded.checksum",
                (name, sequence, serialized, checksum),
            )
        return Checkpoint(name, sequence, payload, checksum)

    def load(self, name: str) -> Checkpoint:
        row = self.connection.execute(
            "SELECT sequence, payload, checksum FROM checkpoints WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise KeyError("checkpoint_missing")
        sequence, serialized, checksum = row
        if hashlib.sha256(serialized.encode()).hexdigest() != checksum:
            raise ValueError("checkpoint_integrity_failure")
        payload = json.loads(serialized)
        if not isinstance(payload, dict):
            raise ValueError("checkpoint_payload_invalid")
        return Checkpoint(name, int(sequence), payload, checksum)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SQLiteCheckpointStore":
        return self

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> None:
        self.close()
