pub mod codec;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub enum SessionState {
    Disabled,
    Connecting,
    Ready,
    Degraded,
    Halted,
    Uncertain,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct VenuePermission {
    pub venue_id: u16,
    pub broker_id: u16,
    pub branch_id: u64,
    pub entity_id: u64,
    pub allowed: bool,
    pub live_enabled: bool,
    pub max_messages_per_second: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct SessionLease {
    pub venue_id: u16,
    pub branch_id: u64,
    pub epoch: u64,
    pub owner_id: String,
    pub expires_at_ns: u64,
    pub state: SessionState,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub enum AuthorizationFailure {
    VenueNotAllowed,
    BranchMismatch,
    EntityMismatch,
    LiveDisabled,
    SessionNotReady,
    LeaseExpired,
    LeaseOwnerMismatch,
    RateExceeded,
}

pub fn authorize(
    permission: &VenuePermission,
    lease: &SessionLease,
    branch_id: u64,
    entity_id: u64,
    live: bool,
    owner_id: &str,
    now_ns: u64,
    messages_per_second: u64,
) -> Result<(), AuthorizationFailure> {
    if !permission.allowed {
        return Err(AuthorizationFailure::VenueNotAllowed);
    }
    if permission.branch_id != branch_id || lease.branch_id != branch_id {
        return Err(AuthorizationFailure::BranchMismatch);
    }
    if permission.venue_id != lease.venue_id
        || permission.venue_id == 0
        || permission.broker_id == 0
        || lease.epoch == 0
    {
        return Err(AuthorizationFailure::VenueNotAllowed);
    }
    if permission.entity_id != entity_id {
        return Err(AuthorizationFailure::EntityMismatch);
    }
    if live && !permission.live_enabled {
        return Err(AuthorizationFailure::LiveDisabled);
    }
    if lease.state != SessionState::Ready {
        return Err(AuthorizationFailure::SessionNotReady);
    }
    if lease.expires_at_ns <= now_ns {
        return Err(AuthorizationFailure::LeaseExpired);
    }
    if lease.owner_id != owner_id {
        return Err(AuthorizationFailure::LeaseOwnerMismatch);
    }
    if messages_per_second > permission.max_messages_per_second {
        return Err(AuthorizationFailure::RateExceeded);
    }
    Ok(())
}

pub fn lease_digest(lease: &SessionLease) -> String {
    let bytes = serde_json::to_vec(lease).unwrap_or_default();
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn permission() -> VenuePermission {
        VenuePermission {
            venue_id: 5,
            broker_id: 8,
            branch_id: 11,
            entity_id: 21,
            allowed: true,
            live_enabled: false,
            max_messages_per_second: 100,
        }
    }

    fn lease() -> SessionLease {
        SessionLease {
            venue_id: 5,
            branch_id: 11,
            epoch: 4,
            owner_id: "node-a".to_owned(),
            expires_at_ns: 1000,
            state: SessionState::Ready,
        }
    }

    #[test]
    fn allows_restricted_simulation() {
        assert!(authorize(&permission(), &lease(), 11, 21, false, "node-a", 500, 10).is_ok());
    }

    #[test]
    fn rejects_expired_lease() {
        assert_eq!(
            authorize(&permission(), &lease(), 11, 21, false, "node-a", 1000, 10),
            Err(AuthorizationFailure::LeaseExpired)
        );
    }

    #[test]
    fn rejects_venue_mismatch() {
        let mut value = lease();
        value.venue_id = 6;
        assert_eq!(
            authorize(&permission(), &value, 11, 21, false, "node-a", 500, 10),
            Err(AuthorizationFailure::VenueNotAllowed)
        );
    }
}
