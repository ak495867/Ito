from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class TimingEvidence:
    clock_hz: int
    latency_cycles: int
    slack_ps: int
    reset_verified: bool
    cdc_verified: bool

    def validate(self) -> None:
        if self.clock_hz <= 0 or self.latency_cycles < 0:
            raise ValueError("timing_parameters_invalid")
        if not self.reset_verified or not self.cdc_verified:
            raise ValueError("hardware_safety_evidence_missing")


@dataclass(frozen=True)
class FrameEvidence:
    frame_schema: str
    frame_digest: str
    timing: TimingEvidence

    @classmethod
    def create(cls, frame_schema: str, frame: bytes, timing: TimingEvidence) -> "FrameEvidence":
        if not frame_schema:
            raise ValueError("frame_schema_invalid")
        timing.validate()
        return cls(frame_schema, sha256(frame).hexdigest(), timing)

    def validate(self) -> None:
        if len(self.frame_digest) != 64:
            raise ValueError("frame_digest_invalid")
        self.timing.validate()
