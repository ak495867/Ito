# Ito Production-Readiness Assessment

## Decision

Ito is **not fully production-ready for live trading**. It is a substantially deeper simulator and controlled-connectivity foundation with verified C++, Rust, OCaml, SystemVerilog, and Python components. The repository now contains explicit readiness gates so that simulator success cannot be mistaken for venue-certified production readiness.

## Verified in the repository

| Area | Status | Evidence |
| --- | --- | --- |
| C++ exchange simulator | Verified | C++ unit tests and deterministic venue adapter tests |
| Multiple broker and exchange routing | Verified in simulation | Session manager, smart-order router, dual-venue fallback tests |
| TLS transport foundation | Implemented | OpenSSL peer verification and optional client certificate path |
| Risk and circuit breakers | Verified in simulation | OCaml JSON validator and dynamic high-frequency stress engine |
| FPGA controls | Verified in simulation | Venue multiplexer, rate limiter, protocol bridge, risk accelerator testbenches |
| Reconciliation and fencing | Verified in simulation | C++ and Python tests |
| Build and source policy | Verified | Unified build and no-comments checker |
| Benchmarking | Verified as regression model | Four-branch, four-adapter jitter suite with p99 reports |

## Remaining blockers

Production live trading still requires venue-native protocol implementations and certification for every broker and exchange, production identity and credential provisioning through controlled key infrastructure, mutually authenticated session operations, FPGA synthesis and timing closure, clock and network validation on target hardware, hardware-in-the-loop testing, operational telemetry and incident integration, disaster recovery exercises, security testing, independent risk and compliance approval, and controlled canary deployment.

The current network adapter supports a secure TLS foundation but intentionally leaves venue-specific FIX, binary, REST, and WebSocket encoding and session conformance behind adapter-specific certification work. All repository route profiles remain live-disabled. The deployment configuration therefore cannot originate live orders accidentally.

## Release rule

A release may progress from simulator to laboratory only when all simulated gates pass. It may progress from laboratory to venue certification only when target FPGA and network evidence is attached. It may progress to production only when every gate in `docs/production/readiness_matrix.json` is implemented or externally evidenced, with signed artifact, policy, venue, branch, and operator approvals recorded.
