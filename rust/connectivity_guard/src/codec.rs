use sha2::{Digest, Sha256};
use std::convert::TryInto;

pub const MAGIC: u16 = 0x4954;
pub const MAX_PAYLOAD: usize = 4096;
pub const HEADER_BYTES: usize = 88;
pub const SUPPORTED_VERSION: u16 = 1;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WireFrame {
    pub version: u16,
    pub message_type: u16,
    pub flags: u16,
    pub branch_id: u64,
    pub entity_id: u64,
    pub venue_id: u16,
    pub session_epoch: u64,
    pub sequence: u64,
    pub expires_at_ns: u64,
    pub payload_hash: [u8; 32],
    pub payload: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CodecError {
    InvalidMagic,
    UnsupportedVersion,
    PayloadTooLarge,
    Truncated,
    InvalidLength,
    InvalidScope,
    InvalidSequence,
    InvalidExpiry,
    InvalidPayloadHash,
}

impl WireFrame {
    pub fn new(
        version: u16,
        message_type: u16,
        flags: u16,
        branch_id: u64,
        entity_id: u64,
        venue_id: u16,
        session_epoch: u64,
        sequence: u64,
        expires_at_ns: u64,
        payload: Vec<u8>,
    ) -> Result<Self, CodecError> {
        if payload.len() > MAX_PAYLOAD {
            return Err(CodecError::PayloadTooLarge);
        }
        if branch_id == 0
            || entity_id == 0
            || venue_id == 0
            || session_epoch == 0
            || sequence == 0
            || expires_at_ns == 0
        {
            return Err(CodecError::InvalidScope);
        }
        let payload_hash = hash_payload(&payload);
        Ok(Self {
            version,
            message_type,
            flags,
            branch_id,
            entity_id,
            venue_id,
            session_epoch,
            sequence,
            expires_at_ns,
            payload_hash,
            payload,
        })
    }

    pub fn encode(&self) -> Result<Vec<u8>, CodecError> {
        if self.version != SUPPORTED_VERSION {
            return Err(CodecError::UnsupportedVersion);
        }
        if self.branch_id == 0
            || self.entity_id == 0
            || self.venue_id == 0
            || self.session_epoch == 0
            || self.sequence == 0
            || self.expires_at_ns == 0
        {
            return Err(CodecError::InvalidScope);
        }
        if self.payload.len() > MAX_PAYLOAD {
            return Err(CodecError::PayloadTooLarge);
        }
        if self.payload_hash != hash_payload(&self.payload) {
            return Err(CodecError::InvalidPayloadHash);
        }
        let mut bytes = Vec::with_capacity(HEADER_BYTES + self.payload.len());
        bytes.extend_from_slice(&MAGIC.to_le_bytes());
        bytes.extend_from_slice(&self.version.to_le_bytes());
        bytes.extend_from_slice(&self.message_type.to_le_bytes());
        bytes.extend_from_slice(&self.flags.to_le_bytes());
        bytes.extend_from_slice(&self.branch_id.to_le_bytes());
        bytes.extend_from_slice(&self.entity_id.to_le_bytes());
        bytes.extend_from_slice(&self.venue_id.to_le_bytes());
        bytes.extend_from_slice(&0u16.to_le_bytes());
        bytes.extend_from_slice(&self.session_epoch.to_le_bytes());
        bytes.extend_from_slice(&self.sequence.to_le_bytes());
        bytes.extend_from_slice(&self.expires_at_ns.to_le_bytes());
        bytes.extend_from_slice(&(self.payload.len() as u32).to_le_bytes());
        bytes.extend_from_slice(&self.payload_hash);
        bytes.extend_from_slice(&self.payload);
        Ok(bytes)
    }

    pub fn decode(
        bytes: &[u8],
        now_ns: u64,
        expected_branch_id: u64,
        expected_entity_id: u64,
        last_sequence: u64,
    ) -> Result<Self, CodecError> {
        if bytes.len() < HEADER_BYTES {
            return Err(CodecError::Truncated);
        }
        if u16::from_le_bytes(bytes[0..2].try_into().map_err(|_| CodecError::Truncated)?) != MAGIC {
            return Err(CodecError::InvalidMagic);
        }
        let version =
            u16::from_le_bytes(bytes[2..4].try_into().map_err(|_| CodecError::Truncated)?);
        if version != SUPPORTED_VERSION {
            return Err(CodecError::UnsupportedVersion);
        }
        let branch_id =
            u64::from_le_bytes(bytes[8..16].try_into().map_err(|_| CodecError::Truncated)?);
        let entity_id = u64::from_le_bytes(
            bytes[16..24]
                .try_into()
                .map_err(|_| CodecError::Truncated)?,
        );
        let venue_id = u16::from_le_bytes(
            bytes[24..26]
                .try_into()
                .map_err(|_| CodecError::Truncated)?,
        );
        let session_epoch = u64::from_le_bytes(
            bytes[28..36]
                .try_into()
                .map_err(|_| CodecError::Truncated)?,
        );
        let sequence = u64::from_le_bytes(
            bytes[36..44]
                .try_into()
                .map_err(|_| CodecError::Truncated)?,
        );
        let expires_at_ns = u64::from_le_bytes(
            bytes[44..52]
                .try_into()
                .map_err(|_| CodecError::Truncated)?,
        );
        let payload_length = u32::from_le_bytes(
            bytes[52..56]
                .try_into()
                .map_err(|_| CodecError::Truncated)?,
        ) as usize;
        if payload_length > MAX_PAYLOAD {
            return Err(CodecError::PayloadTooLarge);
        }
        if bytes.len() != HEADER_BYTES + payload_length {
            return Err(CodecError::InvalidLength);
        }
        if branch_id != expected_branch_id
            || entity_id != expected_entity_id
            || venue_id == 0
            || session_epoch == 0
        {
            return Err(CodecError::InvalidScope);
        }
        if last_sequence == u64::MAX || sequence != last_sequence + 1 {
            return Err(CodecError::InvalidSequence);
        }
        if expires_at_ns <= now_ns {
            return Err(CodecError::InvalidExpiry);
        }
        let mut payload_hash = [0u8; 32];
        payload_hash.copy_from_slice(&bytes[56..88]);
        let payload = bytes[HEADER_BYTES..].to_vec();
        if payload_hash != hash_payload(&payload) {
            return Err(CodecError::InvalidPayloadHash);
        }
        Ok(Self {
            version,
            message_type: u16::from_le_bytes(
                bytes[4..6].try_into().map_err(|_| CodecError::Truncated)?,
            ),
            flags: u16::from_le_bytes(bytes[6..8].try_into().map_err(|_| CodecError::Truncated)?),
            branch_id,
            entity_id,
            venue_id,
            session_epoch,
            sequence,
            expires_at_ns,
            payload_hash,
            payload,
        })
    }
}

fn hash_payload(payload: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(payload);
    hasher.finalize().into()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trips_frame() {
        let frame = WireFrame::new(1, 32, 0, 11, 21, 5, 4, 9, 2_000, b"order".to_vec()).unwrap();
        assert_eq!(
            WireFrame::decode(&frame.encode().unwrap(), 1_000, 11, 21, 8).unwrap(),
            frame
        );
    }

    #[test]
    fn rejects_scope_mismatch() {
        let frame = WireFrame::new(1, 32, 0, 11, 21, 5, 4, 9, 2_000, b"order".to_vec()).unwrap();
        assert_eq!(
            WireFrame::decode(&frame.encode().unwrap(), 1_000, 12, 21, 8),
            Err(CodecError::InvalidScope)
        );
    }

    #[test]
    fn rejects_expired_frame() {
        let frame = WireFrame::new(1, 32, 0, 11, 21, 5, 4, 9, 1_000, b"order".to_vec()).unwrap();
        assert_eq!(
            WireFrame::decode(&frame.encode().unwrap(), 1_000, 11, 21, 8),
            Err(CodecError::InvalidExpiry)
        );
    }

    #[test]
    fn rejects_oversized_frame() {
        let frame = WireFrame::new(1, 32, 0, 11, 21, 5, 4, 9, 2_000, vec![0; MAX_PAYLOAD + 1]);
        assert_eq!(frame, Err(CodecError::PayloadTooLarge));
    }
}
