from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


class StoreError(RuntimeError):
    pass


class DurableEventStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL UNIQUE,
                correlation_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                timestamp_ns INTEGER NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                name TEXT PRIMARY KEY,
                sequence INTEGER NOT NULL,
                payload TEXT NOT NULL,
                sha256 TEXT NOT NULL
            );
        """)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def append(
        self,
        event_id: int,
        correlation_id: int,
        event_type: str,
        timestamp_ns: int,
        payload: dict[str, object],
    ) -> int:
        if min(event_id, correlation_id, timestamp_ns) <= 0 or not event_type:
            raise StoreError("event_invalid")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        try:
            with self.connection:
                self.connection.execute(
                    "INSERT INTO events(event_id, correlation_id, event_type, timestamp_ns, payload) VALUES (?, ?, ?, ?, ?)",
                    (event_id, correlation_id, event_type, timestamp_ns, serialized),
                )
        except sqlite3.IntegrityError as error:
            raise StoreError("duplicate_event") from error
        return int(
            self.connection.execute(
                "SELECT sequence FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()[0]
        )

    def last_sequence(self) -> int:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM events"
        ).fetchone()
        return int(row[0])

    def events(self, start_sequence: int = 1) -> list[dict[str, object]]:
        if start_sequence <= 0:
            raise StoreError("sequence_invalid")
        rows = self.connection.execute(
            "SELECT sequence, event_id, correlation_id, event_type, timestamp_ns, payload FROM events WHERE sequence >= ? ORDER BY sequence",
            (start_sequence,),
        ).fetchall()
        return [
            {
                "sequence": sequence,
                "event_id": event_id,
                "correlation_id": correlation_id,
                "event_type": event_type,
                "timestamp_ns": timestamp_ns,
                "payload": json.loads(payload),
            }
            for sequence, event_id, correlation_id, event_type, timestamp_ns, payload in rows
        ]

    def write_snapshot(self, name: str, payload: dict[str, object]) -> None:
        if not name:
            raise StoreError("snapshot_name_invalid")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        with self.connection:
            self.connection.execute(
                "INSERT INTO snapshots(name, sequence, payload, sha256) VALUES (?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET sequence=excluded.sequence, payload=excluded.payload, sha256=excluded.sha256",
                (name, self.last_sequence(), serialized, checksum),
            )

    def read_snapshot(self, name: str) -> dict[str, object]:
        row = self.connection.execute(
            "SELECT sequence, payload, sha256 FROM snapshots WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise StoreError("snapshot_missing")
        sequence, serialized, checksum = row
        if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != checksum:
            raise StoreError("snapshot_integrity_failure")
        return {
            "name": name,
            "sequence": int(sequence),
            "payload": json.loads(serialized),
            "sha256": checksum,
        }

    def verify_recovery(self) -> None:
        sequences = [
            row[0]
            for row in self.connection.execute(
                "SELECT sequence FROM events ORDER BY sequence"
            ).fetchall()
        ]
        if sequences != list(range(1, len(sequences) + 1)):
            raise StoreError("sequence_continuity_failure")
        for name, sequence, serialized, checksum in self.connection.execute(
            "SELECT name, sequence, payload, sha256 FROM snapshots"
        ):
            if (
                sequence > len(sequences)
                or hashlib.sha256(serialized.encode("utf-8")).hexdigest() != checksum
            ):
                raise StoreError(f"snapshot_recovery_failure:{name}")

    def __enter__(self) -> "DurableEventStore":
        return self

    def __exit__(
        self, exception_type: object, exception: object, traceback: object
    ) -> None:
        self.close()
