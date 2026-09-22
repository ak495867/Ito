pub mod codec;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fmt;
use std::io::Write;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

static AUDIT_LOG: std::sync::Mutex<Option<std::fs::File>> = std::sync::Mutex::new(None);

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
    JsonParseError,
    ConfigMissing,
    TlsHandshakeFailed,
    ConnectionPoolExhausted,
    ProtocolViolation,
    SequenceOutOfOrder,
    PayloadSizeExceeded,
    SignatureVerificationFailed,
}

impl fmt::Display for AuthorizationFailure {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AuthorizationFailure::VenueNotAllowed => write!(f, "venue_not_allowed"),
            AuthorizationFailure::BranchMismatch => write!(f, "branch_mismatch"),
            AuthorizationFailure::EntityMismatch => write!(f, "entity_mismatch"),
            AuthorizationFailure::LiveDisabled => write!(f, "live_disabled"),
            AuthorizationFailure::SessionNotReady => write!(f, "session_not_ready"),
            AuthorizationFailure::LeaseExpired => write!(f, "lease_expired"),
            AuthorizationFailure::LeaseOwnerMismatch => write!(f, "lease_owner_mismatch"),
            AuthorizationFailure::RateExceeded => write!(f, "rate_exceeded"),
            AuthorizationFailure::JsonParseError => write!(f, "json_parse_error"),
            AuthorizationFailure::ConfigMissing => write!(f, "config_missing"),
            AuthorizationFailure::TlsHandshakeFailed => write!(f, "tls_handshake_failed"),
            AuthorizationFailure::ConnectionPoolExhausted => write!(f, "connection_pool_exhausted"),
            AuthorizationFailure::ProtocolViolation => write!(f, "protocol_violation"),
            AuthorizationFailure::SequenceOutOfOrder => write!(f, "sequence_out_of_order"),
            AuthorizationFailure::PayloadSizeExceeded => write!(f, "payload_size_exceeded"),
            AuthorizationFailure::SignatureVerificationFailed => write!(f, "signature_verification_failed"),
        }
    }
}
 

static EVENT_ID: AtomicU64 = AtomicU64::new(1);


#[derive(Clone, Debug, Serialize)]
pub struct AuditEntry {
    pub event_id: u64,
    pub timestamp_ns: u64,
    pub event_type: String,
    pub details: String,
}

impl AuditEntry {
    pub fn new(event_type: &str, details: &str) -> Self {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;
        let event_id = EVENT_ID.fetch_add(1, Ordering::Relaxed);
        Self {
            event_id,
            timestamp_ns: now,
            event_type: event_type.to_string(),
            details: details.to_string(),
        }
    }

    pub fn log(&self) {
        if let Ok(mut guard) = AUDIT_LOG.lock() {
            if let Some(ref mut file) = *guard {
                let _ = writeln!(file, "{:?}", self);
            }
        }
    }
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub enum ConnectionEvent {
    ConnectAttempt {
        host: String,
        port: u16,
        success: bool,
    },
    ConnectionEstablished {
        venue_id: u16,
        duration_ns: u64,
    },
    ConnectionClosed {
        venue_id: u16,
        reason: String,
    },
    MessageReceived {
        venue_id: u16,
        message_type: u16,
        size: usize,
    },
    MessageSent {
        venue_id: u16,
        size: usize,
    },
    Authorization {
        venue_id: u16,
        success: bool,
        failure_reason: Option<AuthorizationFailure>,
    },
    PoolFull,
    PoolReused,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct RateStats {
    pub messages_per_second: u64,
    pub messages_total: u64,
    pub last_reset_ns: u64,
}

impl RateStats {
    pub fn new() -> Self {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;
        Self {
            messages_per_second: 0,
            messages_total: 0,
            last_reset_ns: now,
        }
    }

    pub fn record(&mut self) {
        self.messages_total += 1;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;
        let second = now / 1_000_000_000;
        if second > self.last_reset_ns / 1_000_000_000 {
            self.messages_per_second = 1;
            self.last_reset_ns = now;
        } else {
            self.messages_per_second += 1;
        }
    }

    pub fn snapshot(&self) -> (u64, u64) {
        (self.messages_per_second, self.messages_total)
    }
}

pub struct ConnectivityLogger {
    audit_file: Option<std::fs::File>,
    rate_stats: Mutex<RateStats>,
}

impl ConnectivityLogger {
    pub fn new(audit_path: &str) -> Self {
        let rate_stats = Mutex::new(RateStats::new());
        let audit_file = if !audit_path.is_empty() {
            std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(audit_path)
                .ok()
        } else {
            None
        };
        ConnectivityLogger {
            audit_file,
            rate_stats,
        }
    }

    pub fn log_event(&self, event: &ConnectionEvent) {
        let details = match event {
            ConnectionEvent::ConnectAttempt { host, port, success } => {
                format!("connect_attempt:{} {} {}", host, port, success)
            }
            ConnectionEvent::ConnectionEstablished { venue_id, duration_ns } => {
                format!("connected:venue_{} duration_{}", venue_id, duration_ns)
            }
            ConnectionEvent::ConnectionClosed { venue_id, reason } => {
                format!("closed:venue_{} reason:{}", venue_id, reason)
            }
            ConnectionEvent::MessageReceived { venue_id, message_type, size } => {
                format!("received:venue_{} type_{} size_{}", venue_id, message_type, size)
            }
            ConnectionEvent::MessageSent { venue_id, size } => {
                format!("sent:venue_{} size_{}", venue_id, size)
            }
            ConnectionEvent::Authorization { venue_id, success, failure_reason } => {
                let reason = failure_reason
                    .as_ref()
                    .map_or_else(|| "unknown".to_string(), |r| r.to_string());
                format!("auth:venue_{} success:{} reason:{}", venue_id, success, reason)
            }
            ConnectionEvent::PoolFull => "pool_full".to_string(),
            ConnectionEvent::PoolReused => "pool_reused".to_string(),
        };
        let entry = AuditEntry::new(&details, "");
        entry.log();

        let mut rate = self.rate_stats.lock().unwrap();
        rate.record();
    }
}

pub fn init_audit_logger(audit_path: &str) -> Result<(), std::io::Error> {
    let mut guard = AUDIT_LOG.lock().unwrap();
    if (*guard).is_none() {
        *guard = Some(std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(audit_path)?);
    }
    Ok(())
}

pub fn shutdown_audit_logger() {
    let mut guard = AUDIT_LOG.lock().unwrap();
    if let Some(ref file) = *guard {
        let _ = file.sync_all();
        drop(file);
    }
    *guard = None;
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct VenueStats {
    pub venue_id: u16,
    pub messages_received: u64,
    pub messages_sent: u64,
    pub authorizations_attempted: u64,
    pub authorizations_successful: u64,
    pub authorizations_failed: u64,
    pub connection_uptime_ns: u64,
}

impl Default for VenueStats {
    fn default() -> Self {
        Self {
            venue_id: 0,
            messages_received: 0,
            messages_sent: 0,
            authorizations_attempted: 0,
            authorizations_successful: 0,
            authorizations_failed: 0,
            connection_uptime_ns: 0,
        }
    }
}

impl VenueStats {
    pub fn record_authorization(&mut self, success: bool) {
        self.authorizations_attempted += 1;
        if success {
            self.authorizations_successful += 1;
        } else {
            self.authorizations_failed += 1;
        }
    }

    pub fn record_message_sent(&mut self) {
        self.messages_sent += 1;
    }

    pub fn record_message_received(&mut self) {
        self.messages_received += 1;
    }
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

pub fn audit_digest(entry: &AuditEntry) -> String {
    let mut hasher = Sha256::new();
    hasher.update(format!(
        "{}:{}:{}:{}:{}:{}",
        entry.event_id, entry.timestamp_ns, entry.event_type, entry.details
    )
    .as_bytes());
    hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_authority_failure_display() {
        assert_eq!(AuthorizationFailure::VenueNotAllowed.to_string(), "venue_not_allowed");
        assert_eq!(AuthorizationFailure::RateExceeded.to_string(), "rate_exceeded");
        assert_eq!(AuthorizationFailure::TlsHandshakeFailed.to_string(), "tls_handshake_failed");
        assert_eq!(AuthorizationFailure::ProtocolViolation.to_string(), "protocol_violation");
        assert_eq!(AuthorizationFailure::PayloadSizeExceeded.to_string(), "payload_size_exceeded");
        assert_eq!(AuthorizationFailure::SignatureVerificationFailed.to_string(), "signature_verification_failed");
    }

    #[test]
    fn test_rate_stats() {
        let mut rate = RateStats::new();
        assert_eq!(rate.messages_per_second, 0);
        assert_eq!(rate.messages_total, 0);

        rate.record();
        rate.record();
        rate.record();

        let (per_second, total) = rate.snapshot();
        assert_eq!(total, 3);
        assert_eq!(per_second, 3);
    }

    #[test]
    fn test_audit_entry_creation() {
        let entry = AuditEntry::new("test_event", "test details");
        assert_eq!(entry.event_id, 1);
        assert!(entry.timestamp_ns > 0);
        assert_eq!(entry.event_type, "test_event");
        assert_eq!(entry.details, "test details");
    }
}