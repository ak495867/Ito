# ADR 0001: Language boundaries

## Decision

Ito uses C++ for latency-sensitive host execution and deterministic service components, Rust for security-sensitive utilities and artifact verification, OCaml for policy validation and configuration semantics, SystemVerilog for FPGA datapaths and execution-boundary controls, and Python for replay, operations, research, and backtest tooling.

## Boundary rules

The FPGA layer accepts only versioned binary contracts. C++ owns orchestration and strategy interfaces. Rust utilities may verify artifacts and emit evidence but cannot activate live trading. OCaml validation must complete before policy artifacts are signed. Python processes have no live execution credentials and operate on copied or replay data.

## Consequences

The repository requires cross-language contract tests, pinned toolchains, compatibility manifests, generated register maps, and release evidence. The language split increases build complexity but makes safety, performance, and operational roles explicit.
