use ito_policy_signer::{digest_bytes, ReleaseBinding};
use std::env;
use std::fs;

fn read(path: &str) -> Vec<u8> {
    match fs::read(path) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("artifact_read_failed:{path}:{error}");
            std::process::exit(1);
        }
    }
}

fn main() {
    let mut arguments = env::args().skip(1);
    let policy_path = arguments
        .next()
        .unwrap_or_else(|| "config/risk/default_risk_policy.json".to_owned());
    let rtl_path = arguments
        .next()
        .unwrap_or_else(|| "rtl/common/generated/risk_frame_pkg.sv".to_owned());
    let schema_path = arguments
        .next()
        .unwrap_or_else(|| "interfaces/schemas/order_intent.schema.json".to_owned());
    let policy = read(&policy_path);
    let policy_json: serde_json::Value = serde_json::from_slice(&policy).unwrap_or_else(|error| {
        eprintln!("policy_invalid:{error}");
        std::process::exit(1);
    });
    let policy_version = policy_json
        .get("policy_version")
        .and_then(serde_json::Value::as_u64)
        .unwrap_or_else(|| {
            eprintln!("policy_version_missing");
            std::process::exit(1);
        });
    let binding = ReleaseBinding {
        policy_version,
        artifact_digest: digest_bytes(&policy),
        rtl_digest: digest_bytes(&read(&rtl_path)),
        schema_digest: digest_bytes(&read(&schema_path)),
    };
    println!(
        "{}",
        serde_json::to_string_pretty(&binding).unwrap_or_default()
    );
}
