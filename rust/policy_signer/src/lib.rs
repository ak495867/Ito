use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct ReleaseBinding {
    pub policy_version: u64,
    pub artifact_digest: String,
    pub rtl_digest: String,
    pub schema_digest: String,
}

pub fn digest_bytes(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hasher.finalize().iter().map(|byte| format!("{byte:02x}")).collect()
}

pub fn digest_json<T: Serialize>(value: &T) -> String {
    let bytes = serde_json::to_vec(value).unwrap_or_default();
    digest_bytes(&bytes)
}

fn valid_digest(value: &str) -> bool {
    value.len() == 64 && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

pub fn verify_binding(binding: &ReleaseBinding) -> bool {
    binding.policy_version > 0 && valid_digest(&binding.artifact_digest) && valid_digest(&binding.rtl_digest) && valid_digest(&binding.schema_digest)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hashes_deterministically() {
        assert_eq!(digest_bytes(b"ito"), digest_bytes(b"ito"));
        assert_eq!(digest_bytes(b"ito").len(), 64);
    }

    #[test]
    fn verifies_release_binding_shape() {
        let binding = ReleaseBinding { policy_version: 2, artifact_digest: "a".repeat(64), rtl_digest: "b".repeat(64), schema_digest: "c".repeat(64) };
        assert!(verify_binding(&binding));
        let invalid = ReleaseBinding { policy_version: 2, artifact_digest: "g".repeat(64), rtl_digest: "b".repeat(64), schema_digest: "c".repeat(64) };
        assert!(!verify_binding(&invalid));
    }
}
