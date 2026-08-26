use sha2::{Digest, Sha256};
use std::env;
use std::fs;

fn main() {
    let mut args = env::args().skip(1);
    let path = args.next().unwrap_or_default();
    let expected = args.next().unwrap_or_default().to_lowercase();
    if path.is_empty() || expected.len() != 64 || !expected.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        eprintln!("usage: ito-artifact-verifier <file> <sha256>");
        std::process::exit(2);
    }
    let data = match fs::read(&path) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    };
    let mut hasher = Sha256::new();
    hasher.update(data);
    let actual = hasher.finalize().iter().map(|byte| format!("{byte:02x}")).collect::<String>();
    if actual != expected {
        eprintln!("artifact_digest_mismatch");
        std::process::exit(1);
    }
    println!("artifact_verified");
}
