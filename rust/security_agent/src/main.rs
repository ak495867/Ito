use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;

#[derive(Debug, Serialize, Deserialize)]
struct ArtifactReport {
    path: String,
    sha256: String,
    bytes: u64,
    verified: bool,
}

fn digest(path: &str, expected: Option<&str>) -> Result<ArtifactReport, String> {
    let data = fs::read(path).map_err(|error| error.to_string())?;
    let mut hasher = Sha256::new();
    hasher.update(&data);
    let hash = hasher.finalize();
    let value = hash.iter().map(|byte| format!("{byte:02x}")).collect::<String>();
    let verified = expected.map(|digest| digest.eq_ignore_ascii_case(&value)).unwrap_or(false);
    Ok(ArtifactReport { path: path.to_owned(), sha256: value, bytes: data.len() as u64, verified })
}

fn main() {
    let path = match env::args().nth(1) {
        Some(value) => value,
        None => {
            eprintln!("usage: ito-security-agent <artifact> [sha256]");
            std::process::exit(2);
        }
    };
    let expected = env::args().nth(2);
    if let Some(value) = expected.as_deref() {
        if value.len() != 64 || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
            eprintln!("expected_digest_invalid");
            std::process::exit(2);
        }
    }
    match digest(&path, expected.as_deref()) {
        Ok(report) => {
            println!("{}", serde_json::to_string(&report).unwrap_or_else(|_| "{}".to_owned()));
            if expected.is_some() && !report.verified {
                std::process::exit(1);
            }
        }
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
