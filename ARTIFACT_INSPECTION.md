# Artifact Inspection Record

## SBOM

`build/release/sbom.json` is valid JSON with format 1 and type `ito-release-provenance`. It contains 26 Rust package components, including the five Ito workspace packages and registry checksums for third-party crates. It records the system dependencies `c++20`, `openssl`, `ocaml`, `iverilog`, and `python3`, plus a deterministic `source_sha256`.

The SBOM is a dependency inventory and provenance record. It is not a vulnerability scan, license approval, signed attestation, or substitute for an organization-wide software supply-chain review.

## Release binding

`build/release/binding.json` is valid JSON with `policy_version` 2 and three 64-character lowercase hexadecimal SHA-256 digests: `artifact_digest`, `rtl_digest`, and `schema_digest`. The final build executed `scripts/operations/verify_release_binding.py`, which recomputed and matched all three digests.

The binding proves content consistency among the selected policy, generated RTL package, and order schema. It does not prove signer authenticity or hardware-backed key custody; those remain part of the unresolved HSM/KMS production gate.

## Final operational evidence

The final evidence run passed the complete build, 25 Python tests, 7 CTest tests, Rust and OCaml validation, all RTL benches, backup archive integrity, restored-file byte comparisons, portfolio snapshot generation, six-gate simulation, and no-comments enforcement. The readiness result remains `not_production_ready` with 6 external blockers.
