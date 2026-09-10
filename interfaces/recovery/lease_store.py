from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Lease:
    resource: str
    owner_id: str
    fencing_token: int
    expires_at_ns: int


class LeaseStore(Protocol):
    def acquire(self, resource: str, owner_id: str, now_ns: int, ttl_ns: int) -> Lease | None: ...
    def renew(self, lease: Lease, now_ns: int, ttl_ns: int) -> Lease | None: ...
    def release(self, lease: Lease) -> bool: ...


class InMemoryLeaseStore:
    def __init__(self) -> None:
        self._leases: dict[str, Lease] = {}
        self._tokens: dict[str, int] = {}

    def acquire(self, resource: str, owner_id: str, now_ns: int, ttl_ns: int) -> Lease | None:
        if not resource or not owner_id or now_ns < 0 or ttl_ns <= 0:
            raise ValueError("lease_request_invalid")
        current = self._leases.get(resource)
        if current is not None and current.expires_at_ns > now_ns:
            return None
        token = self._tokens.get(resource, 0) + 1
        self._tokens[resource] = token
        lease = Lease(resource, owner_id, token, now_ns + ttl_ns)
        self._leases[resource] = lease
        return lease

    def renew(self, lease: Lease, now_ns: int, ttl_ns: int) -> Lease | None:
        current = self._leases.get(lease.resource)
        if current != lease or now_ns >= lease.expires_at_ns or ttl_ns <= 0:
            return None
        renewed = Lease(lease.resource, lease.owner_id, lease.fencing_token, now_ns + ttl_ns)
        self._leases[lease.resource] = renewed
        return renewed

    def release(self, lease: Lease) -> bool:
        if self._leases.get(lease.resource) != lease:
            return False
        del self._leases[lease.resource]
        return True
