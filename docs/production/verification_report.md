# Ito Verification and Readiness Report

## Executive decision

Ito is **not fully production-ready for live trading**. The current release is a simulator-oriented internal trading-system foundation with explicit fail-closed controls. Every configured exchange and broker profile remains `live_enabled: false`, and the readiness checker reports unresolved external gates rather than allowing a normal build to promote the system to live operation.

## Validation completed

| Validation area | Result | Evidence |
| --- | --- | --- |
| Source policy | Passed | `python3 scripts/check_no_comments.py` returned `no_source_comments` |
| C++ build | Passed | CMake build with OpenSSL 3 TLS linkage |
| C++ tests | Passed | 7 of 7 CTest tests, including journal restart/escaping, endpoint connector, routing, and lifecycle coverage |
| Release integrity | Passed | Policy, generated RTL, and schema digests were recomputed and matched the release binding |
| Recovery drill | Passed | Selected configuration was archived, manifest-verified, and restored atomically |
| Key rotation drill | Passed locally | Ephemeral two-version rotation invariant passed; HSM/KMS evidence remains external |
| Rust workspace | Passed | Connectivity guard, policy signer, risk service, artifact verifier, and security-agent test targets completed successfully |
| OCaml policy validation | Passed | Risk and circuit-breaker JSON validation executable |
| OCaml dynamic stress | Passed | 100,000 violation path, policy replacement, manual clear, and retrip behavior; output `dynamic_policy_open:1` |
| Python tests | Passed | 24 unit tests, including route, replay, quote, portfolio, durable-store, recovery, health, exporter, and release-binding regressions |
| RTL verification | Passed | Pre-trade, exchange bridge, risk accelerator, connectivity control, and rate limiter markers |
| Readiness gate | Correctly blocked | 12 of 18 gates implemented; 6 external blockers remain |

The SystemVerilog runs emit Icarus informational `sorry` messages about constant selects in `always_*` processes. These did not fail the simulation, but they are not evidence of vendor synthesis, timing closure, clock-domain-crossing proof, formal verification, or hardware-in-the-loop validation.

## Multi-branch latency evidence

The expanded benchmark covers four branches, four simulator adapters, and 5,000 messages per branch and adapter per jitter scenario. It uses deterministic virtual timestamps and therefore measures a regression model rather than physical network behavior.

| Simulated jitter | Exchange-A p99 | Exchange-B p99 | Broker-A p99 | Broker-B p99 | Aggregate p99 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 ns | 53,178 ns | 55,698 ns | 58,476 ns | 61,347 ns | 60,571 ns |
| 1,000 ns | 57,116 ns | 60,051 ns | 62,925 ns | 65,855 ns | 64,138 ns |
| 5,000 ns | 76,230 ns | 78,637 ns | 81,985 ns | 84,984 ns | 81,408 ns |
| 10,000 ns | 99,990 ns | 103,385 ns | 106,569 ns | 109,387 ns | 105,170 ns |

The separate 10,000-message-per-branch expanded run produced 160,000 modeled messages with aggregate p99 of 81,363 ns at 5,000 ns jitter. In the suite, `broker-b-sim` is the highest-tail adapter and `exchange-a-sim` is the lowest-tail adapter at every listed jitter level. These figures must not be used as production capacity, execution-quality, or venue-latency claims.

## Remaining blockers

The readiness matrix identifies six unresolved gates: production HSM or KMS-backed key provisioning and rotation, venue-native protocol certification, live credential and session conformance, FPGA synthesis and timing/CDC/formal/HIL evidence, production observability and incident integration, and independent risk, compliance, and change approval. Durable distributed storage, disaster-recovery restoration exercises, penetration testing, and legal sign-off also remain deployment prerequisites even where they are represented as external evidence rather than repository code. The repository now fail-closes on missing live mode, authorization, lease, mTLS, scope, sequence, expiry, payload digest, release digest, recovery manifest, portfolio exposure, and short-sale policy inputs, but these controls are not substitutes for external certification or regulated operational approval.

The TLS connector now provides TLS 1.3 minimum-version enforcement, peer certificate verification, hostname verification, configurable CA roots, required client certificate and key loading, and a live-enable guard. Network submissions remain explicitly uncertain until venue acknowledgment, and routing stops blind fallback after an uncertain outcome. A controlled endpoint with real certificates, authenticated protocol envelopes, venue certification, and external key management is still required before making any production connectivity claim.

## Release artifacts

The readiness matrix is `docs/production/readiness_matrix.json`. The checker is `scripts/production/readiness_check.py`. The deployment template is `infra/docker/compose.production.template.yml`. The complete deterministic benchmark output and chart are under `docs/benchmarks`, and the unified build is `scripts/build_all.sh`.

## References

[1]: ../production/readiness_matrix.json "Ito production-readiness matrix"
[2]: ../benchmarks/multibranch_suite_report.md "Ito multi-branch p99 benchmark suite"
[3]: ../../scripts/build_all.sh "Ito unified build and verification workflow"
[4]: ../../cpp/ito_connectivity/endpoint_connector.cpp "Ito TLS endpoint connector"
[5]: ../../ocaml/circuit_breaker/dynamic_engine.ml "Ito dynamic circuit-breaker stress engine"
