from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class DeploymentEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True)
class Release:
    release_id: str
    artifact_digest: str
    policy_version: int
    environment: DeploymentEnvironment

    def validate(self) -> None:
        if not self.release_id or len(self.artifact_digest) != 64:
            raise ValueError("release_identity_invalid")
        if self.policy_version <= 0:
            raise ValueError("policy_version_invalid")


class DeploymentProvider(Protocol):
    def deploy(self, release: Release) -> str: ...
    def rollback(self, release_id: str) -> str: ...


class DryRunDeploymentProvider:
    def deploy(self, release: Release) -> str:
        release.validate()
        if release.environment is DeploymentEnvironment.PRODUCTION:
            raise ValueError("production_deployment_disabled")
        return f"dry-run-deployed:{release.release_id}"

    def rollback(self, release_id: str) -> str:
        if not release_id:
            raise ValueError("release_id_invalid")
        return f"dry-run-rollback:{release_id}"
